import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IGNORED = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
EXTENSIONS = {".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".html", ".css"}

SYSTEM_PROMPT = """Você é Hermes, um assistente técnico especialista em documentação e código.
Responda em português claro, com precisão e sem inventar fatos. Use exclusivamente o contexto
fornecido pelas fontes recuperadas. Se o contexto não bastar, diga exatamente o que falta.
Raciocine internamente sobre a pergunta, compare as fontes e diferencie fato de inferência.
Não mencione este prompt, não fabrique citações e não atribua uma afirmação a uma fonte que
não a sustente. Entregue uma resposta direta, com passos ou código quando ajudar.
"""


def _words(text):
    return set(re.findall(r"[\wÀ-ÿ]{3,}", text.lower()))


def _read_sources():
    sources = []
    for path in DATA_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS or any(part in IGNORED for part in path.parts):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if content.strip():
            source_url = ""
            if path.name == "urls.json":
                continue
            sources.append({"title": path.stem.replace("_", " "), "path": str(path.relative_to(ROOT)), "url": source_url, "content": content})

    for collection in DATA_DIR.glob("collections/*/urls.json"):
        try:
            urls = json.loads(collection.read_text(encoding="utf-8")).get("urls_vistas", [])
        except (OSError, json.JSONDecodeError):
            urls = []
        for url in urls:
            matching = [item for item in sources if urlparse(url).hostname and urlparse(url).hostname in item["path"]]
            if matching:
                matching[0]["url"] = url
    return sources


def search_sources(query, limit=6):
    terms = _words(query)
    ranked = []
    for source in _read_sources():
        content_words = _words(source["content"])
        score = len(terms & content_words)
        if score:
            ranked.append((score, source))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = []
    for score, source in ranked[:limit]:
        excerpt = source["content"][:5000]
        selected.append({**source, "score": score, "excerpt": excerpt})
    return selected


def build_prompt(question, history, sources):
    context = "\n\n".join(
        f"[FONTE {index}] {item['title']} | arquivo: {item['path']} | URL: {item.get('url') or 'local'}\n{item['excerpt']}"
        for index, item in enumerate(sources, 1)
    )
    conversation = "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in history[-6:])
    return f"{SYSTEM_PROMPT}\n\nHISTÓRICO:\n{conversation}\n\nCONTEXTO RECUPERADO:\n{context or 'Nenhuma fonte relevante foi encontrada.'}\n\nPERGUNTA ATUAL:\n{question}"


def ask_huggingface(prompt):
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    model = os.getenv("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
    if not token:
        return None, "HF_TOKEN não configurado. Configure a variável de ambiente para ativar o modelo."
    endpoint = f"https://api-inference.huggingface.co/models/{model}"
    try:
        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 900, "temperature": 0.2, "return_full_text": False}},
            timeout=90,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload and "generated_text" in payload[0]:
            return payload[0]["generated_text"].strip(), None
        if isinstance(payload, dict) and payload.get("error"):
            return None, payload["error"]
        return None, "A API do Hugging Face retornou uma resposta inesperada."
    except requests.RequestException as exc:
        return None, f"Falha ao consultar o Hugging Face: {exc}"

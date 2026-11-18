import json
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from loaders.gitloader import download_repo
from loaders.scraper import scraper_docs

from .rag import ask_huggingface, build_prompt, search_sources


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
executor = ThreadPoolExecutor(max_workers=2)


def frontend(request):
    return FileResponse(open(FRONTEND / "index.html", "rb"), content_type="text/html; charset=utf-8")


def frontend_asset(request, asset):
    path = (FRONTEND / asset).resolve()
    if FRONTEND not in path.parents or not path.is_file():
        return HttpResponse(status=404)
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return FileResponse(open(path, "rb"), content_type=content_type)


def status(request):
    sources = search_sources("documentation", limit=1000)
    collections = list((ROOT / "data" / "collections").glob("*/"))
    repos = list((ROOT / "data" / "repos").glob("*/"))
    return JsonResponse({"ok": True, "source_count": len(sources), "collections": [p.name for p in collections], "repositories": [p.name for p in repos], "hf_configured": bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY"))})


def _json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


@csrf_exempt
def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    question = str(payload.get("message", "")).strip()
    if not question:
        return JsonResponse({"error": "A mensagem é obrigatória."}, status=400)
    sources = search_sources(question)
    prompt = build_prompt(question, payload.get("history", []), sources)
    answer, error = ask_huggingface(prompt)
    steps = [
        {"label": "Entendi a pergunta", "detail": f"Identifiquei o objetivo técnico e {len(question.split())} palavras-chave."},
        {"label": "Busquei na base local", "detail": f"Comparei os documentos indexados e encontrei {len(sources)} fonte(s) relevante(s)."},
        {"label": "Selecionei evidências", "detail": "Priorizei os trechos com maior sobreposição semântica com a pergunta."},
        {"label": "Preparei a resposta", "detail": "A resposta foi sintetizada pelo modelo usando apenas o contexto recuperado."},
    ]
    if error:
        answer = "Ainda não consigo consultar o modelo de IA. " + error
        steps[-1]["detail"] = "A recuperação funcionou, mas a chamada ao modelo não foi concluída."
    citations = [{"title": item["title"], "path": item["path"], "url": item.get("url") or None, "score": item["score"]} for item in sources]
    return JsonResponse({"answer": answer, "steps": steps, "sources": citations, "model": os.getenv("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct"), "error": error})


@csrf_exempt
def ingest_docs(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    url = str(payload.get("url", "")).strip()
    if not url:
        return JsonResponse({"error": "Informe a URL da documentação."}, status=400)
    collection = str(payload.get("collection", "docs")).strip() or "docs"
    future = executor.submit(scraper_docs, nome_colecao=collection, url=url, versao=payload.get("version") or None, acessar_links_internos=bool(payload.get("follow_links", True)), batch_size=int(payload.get("batch_size", 10)), profundidade=int(payload.get("depth", 10)))
    return JsonResponse({"queued": True, "collection": collection, "message": "Coleta iniciada. O conteúdo ficará disponível para o chat ao terminar."}, status=202)


@csrf_exempt
def ingest_repo(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    url = str(payload.get("url", "")).strip()
    if not url.startswith(("https://github.com/", "http://github.com/")):
        return JsonResponse({"error": "Informe uma URL pública do GitHub."}, status=400)
    executor.submit(download_repo, url)
    return JsonResponse({"queued": True, "message": "Repositório adicionado à fila de indexação."}, status=202)

"""Documentation collection loader."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts = []
        self.links = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def scraper_docs(
    nome_colecao: str = "docs",
    url: str = "",
    versao: str | None = None,
    acessar_links_internos: bool = True,
    batch_size: int = 10,
    profundidade: int = 2,
) -> dict:
    if not url:
        raise ValueError("URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP(S) documentation URLs are supported")
    collection = re.sub(r"[^A-Za-z0-Z0-9_.-]+", "-", nome_colecao).strip("-") or "docs"
    output = Path(__file__).resolve().parents[2] / "data" / "collections" / collection
    output.mkdir(parents=True, exist_ok=True)
    seen = set()
    queue = [(url, 0)]
    saved = 0
    urls_seen = []
    while queue and saved < batch_size:
        current, depth = queue.pop(0)
        if current in seen or depth > profundidade:
            continue
        seen.add(current)
        urls_seen.append(current)
        request = Request(current, headers={"User-Agent": "OROS-Documentation-Collector/1.0"})
        with urlopen(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "text/plain"}:
                continue
            raw = response.read().decode("utf-8", errors="replace")
        if content_type == "text/html":
            parser = _TextParser()
            parser.feed(raw)
            text = "\n".join(parser.parts)
            links = parser.links
        else:
            text = raw
            links = []
        if text.strip():
            name = re.sub(r"[^A-Za-Z0-9]+", "-", urlparse(current).path).strip("-") or "index"
            (output / f"{name}-{saved + 1}.txt").write_text(text, encoding="utf-8")
            saved += 1
        if acessar_links_internos and depth < profundidade:
            for link in links:
                absolute = urljoin(current, link)
                if urlparse(absolute).netloc == parsed.netloc:
                    queue.append((absolute, depth + 1))
    (output / "urls.json").write_text(json.dumps({"urls_vistas": urls_seen}, ensure_ascii=False), encoding="utf-8")
    return {"saved": saved, "urls": urls_seen, "version": versao}

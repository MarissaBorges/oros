"""Local research extraction and report generation."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote_plus, urljoin
from urllib.request import Request, urlopen


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text = []
        self.links = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text.append(data.strip())

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def search(query: str, max_results: int = 8) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 OROSResearch/1.0"})
    results = []
    with urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
    for match in re.finditer(r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>', raw, re.I | re.S):
        target = html.unescape(match.group(1))
        title = re.sub(r"<[^>]+>", "", html.unescape(match.group(2))).strip()
        snippet_match = re.search(r'<a rel="nofollow" class="result__snippet"[^>]*>(.*?)</a>', raw[match.end():], re.I | re.S)
        snippet = re.sub(r"<[^>]+>", "", html.unescape(snippet_match.group(1))).strip() if snippet_match else ""
        if target.startswith("//duckduckgo.com/l/?"):
            from urllib.parse import parse_qs, urlparse
            target = parse_qs(urlparse(target).query).get("uddg", [target])[0]
        results.append({"title": title, "url": target, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def extract(url: str, max_chars: int = 15000) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 OROSResearch/1.0"})
    with urlopen(request, timeout=30) as response:
        content_type = response.headers.get_content_type()
        raw = response.read().decode("utf-8", errors="replace")
    if content_type not in {"text/html", "text/plain"}:
        return {"ok": False, "error": f"Unsupported content type: {content_type}"}
    parser = _TextParser()
    parser.feed(raw)
    text = "\n".join(parser.text)
    title = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    title_text = re.sub(r"<[^>]+>", "", html.unescape(title.group(1))).strip() if title else url
    return {"ok": True, "url": url, "title": title_text, "text": text[:max_chars]}


def create_report(query: str, results: list[dict], vault_root: Path) -> dict:
    now = datetime.now()
    folder = vault_root / "05 Recursos" / "OROS" / "Pesquisas"
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9À-ÿ]+", "-", query).strip("-")[:80] or "Pesquisa"
    path = folder / f"{now.strftime('%Y-%m-%d')}-{safe_name}.md"
    lines = [
        f"# Pesquisa: {query}",
        "",
        f"Gerado pelo OROS em {now.isoformat(timespec='minutes')}",
        "",
        "## Fontes",
        "",
    ]
    for result in results:
        lines.extend([
            f"### {result['title']}",
            f"- URL: {result['url']}",
            f"- Resumo: {result.get('snippet', '')}",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "path": str(path.relative_to(vault_root)), "absolute_path": str(path)}

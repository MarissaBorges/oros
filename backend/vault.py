"""Safe Obsidian/Markdown vault operations for OROS.

This module reuses OpenJarvis's vault integration concept while adding atomic
and path-safe write operations for OROS.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
SKIPPED_DIRS = {".obsidian", ".git", ".trash", "node_modules", ".venv", "__pycache__"}


class VaultError(ValueError):
    pass


class Vault:
    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise VaultError(f"Vault does not exist: {self.root}")

    def _resolve(self, relative_path: str) -> Path:
        if not relative_path or "\x00" in relative_path:
            raise VaultError("Invalid vault path")
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and not candidate.is_relative_to(self.root):
            raise VaultError("Path is outside the vault")
        if any(part in SKIPPED_DIRS for part in candidate.relative_to(self.root).parts):
            raise VaultError("Hidden or system vault directory")
        if candidate.suffix.lower() not in TEXT_EXTENSIONS:
            raise VaultError("Only Markdown and text notes can be edited")
        return candidate

    def list_notes(self, directory: str = "") -> list[dict]:
        base = self._resolve(directory) if directory else self.root
        if not base.is_dir():
            raise VaultError("Directory does not exist")
        notes = []
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if any(part in SKIPPED_DIRS or part.startswith(".") for part in path.relative_to(self.root).parts):
                continue
            stat = path.stat()
            notes.append({
                "path": str(path.relative_to(self.root)),
                "name": path.stem,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        return notes

    def search(self, query: str, limit: int = 20) -> list[dict]:
        terms = [term.casefold() for term in query.split() if term.strip()]
        if not terms:
            raise VaultError("Search query is required")
        matches = []
        for note in self.list_notes():
            path = self.root / note["path"]
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            folded = text.casefold()
            if all(term in folded for term in terms):
                lines = text.splitlines()
                snippet = next(
                    (line.strip() for line in lines if all(term in line.casefold() for term in terms)),
                    lines[0].strip() if lines else "",
                )
                matches.append({"path": note["path"], "title": note["name"], "snippet": snippet[:500]})
                if len(matches) >= limit:
                    break
        return matches

    def read(self, relative_path: str) -> dict:
        path = self._resolve(relative_path)
        if not path.is_file():
            raise VaultError("Note does not exist")
        return {
            "path": relative_path,
            "content": path.read_text(encoding="utf-8"),
            "obsidian_url": f"obsidian://open?vault={self.root.name}&file={relative_path}",
        }

    def write(self, relative_path: str, content: str, mode: str = "write") -> dict:
        path = self._resolve(relative_path)
        if mode not in {"write", "append"}:
            raise VaultError("Mode must be 'write' or 'append'")
        path.parent.mkdir(parents=True, exist_ok=True)
        previous = path.read_text(encoding="utf-8") if path.exists() and mode == "append" else ""
        output = previous + content if mode == "append" else content
        temp = path.with_name(f".{path.name}.oros-{os.getpid()}.tmp")
        temp.write_text(output, encoding="utf-8")
        os.replace(temp, path)
        return {"path": str(path.relative_to(self.root)), "bytes": len(output.encode("utf-8")), "mode": mode}

    def move(self, relative_path: str, destination: str) -> dict:
        source = self._resolve(relative_path)
        target = self._resolve(destination)
        if not source.is_file():
            raise VaultError("Note does not exist")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        return {"from": relative_path, "to": destination}

    def delete(self, relative_path: str) -> dict:
        path = self._resolve(relative_path)
        if not path.is_file():
            raise VaultError("Note does not exist")
        trash = self.root / ".trash"
        trash.mkdir(exist_ok=True)
        target = trash / f"{path.stem}-{os.getpid()}{path.suffix}"
        path.rename(target)
        return {"deleted": relative_path, "trash": str(target.relative_to(self.root))}

    def graph(self) -> dict:
        nodes = []
        edges = []
        notes = self.list_notes()
        available = {note["path"][:-3] if note["path"].endswith(".md") else note["path"] for note in notes}
        for note in notes:
            path = note["path"]
            source = path[:-3] if path.endswith(".md") else path
            nodes.append({
                "id": source,
                "label": note["name"],
                "path": path,
                "size": note["size"],
            })
            try:
                text = (self.root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for target in re.findall(r"\[\[([^\]|#]+)", text):
                clean = target.strip()
                matches = [item for item in available if item == clean or item.endswith(f"/{clean}") or item.split("/")[-1] == clean]
                for match in matches[:1]:
                    edges.append({"source": source, "target": match})
        return {"ok": True, "nodes": nodes[:3000], "edges": edges[:10000]}

    def frontmatter(self, relative_path: str) -> dict:
        result = self.read(relative_path)
        text = result["content"]
        metadata = {}
        body = text
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end >= 0:
                raw = text[3:end].strip()
                body = text[end + 4:].lstrip("\r\n")
                for line in raw.splitlines():
                    key, separator, value = line.partition(":")
                    if separator:
                        metadata[key.strip()] = value.strip().strip("'\"")
        return {"ok": True, "path": relative_path, "metadata": metadata, "body": body}

    def auto_links(self, limit: int = 100) -> list[dict]:
        notes = self.list_notes()
        suggestions = []
        for note in notes:
            path = note["path"]
            source_path = self.root / path
            try:
                text = source_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            words = {word.casefold() for word in re.findall(r"[\wÀ-ÿ]{5,}", text)}
            links = set(re.findall(r"\[\[([^\]|]+)", text))
            for candidate in notes:
                if candidate["path"] == path:
                    continue
                title = candidate["name"]
                if title.casefold() in links or title.casefold() in text.casefold():
                    continue
                if title.casefold() in words:
                    suggestions.append({
                        "source": path,
                        "suggested_target": candidate["path"],
                        "title": title,
                        "reason": "Title appears in note body",
                    })
                    if len(suggestions) >= limit:
                        return suggestions
        return suggestions

    def daily_garden(self) -> dict:
        journal = self.root / "04 Journal" / "01 Diário"
        journal.mkdir(parents=True, exist_ok=True)
        now = datetime.now()
        path = journal / f"{now.strftime('%Y-%m-%d')}.md"
        if not path.exists():
            path.write_text(
                f"# Diário {now.strftime('%d/%m/%Y')}\n\n"
                "## Foco\n- \n\n## Concluído\n- \n\n## Tarefas esquecidas\n- \n\n"
                "## Ideias\n- \n",
                encoding="utf-8",
            )
        suggestions = self.auto_links(limit=20)
        return {
            "ok": True,
            "daily_note": str(path.relative_to(self.root)),
            "link_suggestions": suggestions,
        }

"""Safe Obsidian/Markdown vault operations for OROS.

This module reuses OpenJarvis's vault integration concept while adding atomic
and path-safe write operations for OROS.
"""

from __future__ import annotations

import os
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

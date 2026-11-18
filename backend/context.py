"""Passive active-context awareness for the Arch Linux desktop."""

from __future__ import annotations

import os
import json
import re
import shutil
import subprocess
from pathlib import Path

from .desktop import active_windows, run


TRACE_PATTERNS = (
    re.compile(r"(?P<file>[A-Za-z0-Z0-9_./-]+\.[A-Za-z0-9]+):(?P<line>\d+)", re.I),
    re.compile(r"(?:File [\"'](?P<pyfile>[^\"']+)[\"'], line (?P<pyline>\d+))", re.I),
)


def clipboard_text() -> dict:
    wl_paste = shutil.which("wl-paste")
    if not wl_paste:
        return {"ok": False, "text": "", "error": "wl-paste unavailable"}
    result = run([wl_paste, "--no-newline"], timeout=5)
    return {
        "ok": result["ok"],
        "text": result["stdout"][:20000],
        "error": result["stderr"] if not result["ok"] else "",
    }


def active_window() -> dict | None:
    result = run(["hyprctl", "-j", "activewindow"], timeout=5)
    if not result["ok"]:
        return None
    try:
        window = json.loads(result["stdout"])
    except (json.JSONDecodeError, UnboundLocalError):
        return None
    return {
        "address": window.get("address"),
        "class": window.get("class"),
        "title": window.get("title"),
        "workspace": window.get("workspace", {}).get("name"),
        "pid": window.get("pid"),
    }


def infer_project(text: str = "") -> dict:
    dev_root = Path("/home/borges/dev")
    combined = f"{text} {active_window() or ''}".casefold()
    candidates = []
    for project in dev_root.iterdir():
        if not project.is_dir() or project.name.startswith("."):
            continue
        if project.name.casefold() in combined:
            candidates.append(project)
    if candidates:
        project = candidates[0]
        return {"detected": True, "name": project.name, "path": str(project)}
    return {"detected": False, "name": "", "path": ""}


def extract_trace_context(text: str) -> dict:
    matches = []
    for pattern in TRACE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.groupdict()
            file_name = value.get("file") or value.get("pyfile")
            line = value.get("line") or value.get("pyline")
            if file_name:
                matches.append({"file": file_name, "line": int(line) if line else None})
    return {"has_trace": bool(matches), "locations": matches[:20]}


def snapshot() -> dict:
    clipboard = clipboard_text()
    active = active_window()
    text = clipboard["text"] if clipboard["ok"] else ""
    return {
        "ok": True,
        "active_window": active,
        "windows": active_windows(),
        "clipboard": {
            "available": clipboard["ok"],
            "text": text[:5000],
            "truncated": len(text) > 5000,
        },
        "trace": extract_trace_context(text),
        "project": infer_project(text),
    }

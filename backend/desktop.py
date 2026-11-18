"""Arch Linux/Hyprland desktop control and screen vision primitives."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


def run(command: list[str], timeout: int = 15) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(exc)}


def active_windows() -> list[dict]:
    if not shutil.which("hyprctl"):
        return []
    result = run(["hyprctl", "-j", "clients"])
    if not result["ok"]:
        return []
    try:
        clients = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return []
    return [
        {
            "address": client.get("address"),
            "class": client.get("class"),
            "title": client.get("title"),
            "workspace": client.get("workspace", {}).get("name"),
            "pid": client.get("pid"),
            "visible": client.get("visible"),
            "floating": client.get("floating"),
        }
        for client in clients
    ]


def find_window(query: str) -> dict | None:
    query_folded = query.casefold()
    for window in active_windows():
        haystack = f"{window.get('class', '')} {window.get('title', '')}".casefold()
        if query_folded in haystack:
            return window
    return None


def focus_window(address: str) -> dict:
    if not address or not address.startswith("0x"):
        return {"ok": False, "error": "Invalid Hyprland window address"}
    return run(["hyprctl", "dispatch", "focuswindow", f"address:{address}"])


def open_url(url: str) -> dict:
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("obsidian://")):
        return {"ok": False, "error": "Only HTTP(S) and Obsidian URLs are allowed"}
    return run(["xdg-open", url], timeout=30)


def capture_screen(output_dir: str = "/tmp/oros-captures", filename: str = "screen.png") -> dict:
    grim = shutil.which("grim")
    if not grim:
        return {"ok": False, "error": "grim is not installed"}
    directory = Path(output_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    target = (directory / filename).resolve()
    result = run([grim, str(target)], timeout=30)
    if not result["ok"] or not target.is_file():
        return {"ok": False, "error": result["stderr"] or "Screen capture failed"}
    encoded = base64.b64encode(target.read_bytes()).decode("ascii")
    return {
        "ok": True,
        "path": str(target),
        "mime": "image/png",
        "base64": encoded,
        "windows": active_windows(),
    }

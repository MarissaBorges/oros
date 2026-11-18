"""Browser session discovery and control helpers for OROS."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def find_chrome_debug_sessions() -> list[dict]:
    """Find Chrome-family processes launched with a DevTools debugging port."""
    sessions = []
    proc = Path("/proc")
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            raw = (pid_dir / "cmdline").read_bytes()
            args = [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]
        except (OSError, PermissionError):
            continue
        combined = " ".join(args).casefold()
        if not any(name in combined for name in ("google-chrome", "chromium", "chrome")):
            continue
        port = None
        for arg in args:
            if arg.startswith("--remote-debugging-port="):
                port = arg.split("=", 1)[1]
                break
        if port:
            sessions.append({
                "pid": int(pid_dir.name),
                "browser": "chrome-family",
                "port": int(port),
                "cdp_url": f"http://127.0.0.1:{port}",
            })
    return sessions


def connect_existing_browser(port: int) -> dict:
    """Connect Playwright to an existing Chrome-family session."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "ok": False,
            "error": "Python Playwright is unavailable. Install 'playwright' and browser binaries.",
        }
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        contexts = browser.contexts
        pages = [page for context in contexts for page in context.pages]
        return {
            "ok": True,
            "page_count": len(pages),
            "titles": [page.title() for page in pages],
            "_playwright": playwright,
            "_browser": browser,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

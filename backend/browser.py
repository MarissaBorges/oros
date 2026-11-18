"""Browser session discovery and control helpers for OROS."""

from __future__ import annotations

import os
import urllib.parse
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


def navigate_existing_browser(port: int, url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return {"ok": False, "error": "Only HTTP(S) URLs are allowed"}
    connected = connect_existing_browser(port)
    if not connected["ok"]:
        return connected
    browser = connected.pop("_browser")
    playwright = connected.pop("_playwright")
    try:
        contexts = browser.contexts
        if contexts:
            pages = contexts[0].pages
            page = pages[0] if pages else contexts[0].new_page()
        else:
            context = browser.new_context()
            page = context.new_page()
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        text = page.inner_text("body")[:10000]
        result = {
            "ok": True,
            "url": page.url,
            "title": page.title(),
            "status": response.status if response else None,
            "text": text,
        }
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    finally:
        playwright.stop()
    return result

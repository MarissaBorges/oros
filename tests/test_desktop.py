import json

from backend import desktop


def test_find_window_matches_class_or_title(monkeypatch) -> None:
    windows = [{
        "address": "0x1",
        "class": "google-chrome",
        "title": "OROS - Google Chrome",
        "workspace": "2",
        "visible": True,
    }]
    monkeypatch.setattr(desktop, "active_windows", lambda: windows)

    assert desktop.find_window("chrome")["address"] == "0x1"
    assert desktop.find_window("missing") is None


def test_open_url_rejects_non_web_urls() -> None:
    assert desktop.open_url("file:///etc/passwd")["ok"] is False


def test_active_windows_parses_hyprctl(monkeypatch) -> None:
    payload = [{
        "address": "0x123",
        "class": "zen",
        "title": "OpenJarvis",
        "workspace": {"name": "3"},
        "pid": 42,
        "visible": True,
        "floating": False,
    }]
    monkeypatch.setattr(desktop.shutil, "which", lambda name: "/usr/bin/hyprctl")
    monkeypatch.setattr(desktop, "run", lambda command, timeout=15: {
        "ok": True,
        "returncode": 0,
        "stdout": json.dumps(payload),
        "stderr": "",
    })

    windows = desktop.active_windows()
    assert windows[0]["address"] == "0x123"
    assert windows[0]["title"] == "OpenJarvis"

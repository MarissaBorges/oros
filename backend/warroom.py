"""Hyprland workspace orchestration for OROS focus modes."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .desktop import find_window, focus_window, open_url, run


def notification_mode(enabled: bool) -> dict:
    if shutil.which("makoctl"):
        return run(["makoctl", "mode", "dnd" if not enabled else "default"])
    if shutil.which("dunstctl"):
        return run(["dunstctl", "set-paused", "true" if not enabled else "false"])
    return {"ok": False, "error": "Neither makoctl nor dunstctl is available"}


def start_war_room(project_path: str, note_path: str = "") -> dict:
    project = Path(project_path).expanduser().resolve()
    if not project.is_dir():
        return {"ok": False, "error": "Project directory does not exist"}
    actions = []

    code_window = find_window("code")
    if code_window:
        actions.append(focus_window(code_window["address"]))

    launched_editor = run(["code", str(project)], timeout=20)
    actions.append(launched_editor)

    terminal = run(["kitty", "--directory", str(project)], timeout=20)
    actions.append(terminal)

    if note_path:
        vault_note_url = f"obsidian://open?vault={Path('/home/borges/minha-mente').name}&file={note_path}"
        actions.append(open_url(vault_note_url))

    notification_result = notification_mode(False)
    return {
        "ok": all(action["ok"] for action in actions),
        "project": str(project),
        "note": note_path,
        "notifications_silent": notification_result["ok"],
        "actions": actions,
        "notifications": notification_result,
    }

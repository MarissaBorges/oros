"""Policy-gated terminal operations for OROS."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Iterable


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "oros.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def is_allowed_directory(directory: str, allowed_dirs: Iterable[str]) -> bool:
    path = Path(directory).expanduser().resolve()
    return any(path == Path(item).resolve() or path.is_relative_to(Path(item).resolve()) for item in allowed_dirs)


def validate_command(command: str) -> str | None:
    config = load_config()
    folded = command.casefold()
    for pattern in config.get("blocked_shell_patterns", []):
        if pattern.casefold() in folded:
            return f"Blocked dangerous command pattern: {pattern}"
    return None


def run_command(command: str, working_dir: str = "/home/borges/dev", timeout: int = 60) -> dict:
    if not command.strip():
        return {"ok": False, "error": "Command is required"}
    blocked = validate_command(command)
    if blocked:
        return {"ok": False, "error": blocked}
    config = load_config()
    if not is_allowed_directory(working_dir, config["allowed_shell_dirs"]):
        return {"ok": False, "error": "Working directory is outside the OROS allowlist"}
    safe_env = {key: os.environ[key] for key in ("PATH", "HOME", "USER", "LANG", "TERM") if key in os.environ}
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=max(1, min(timeout, 300)),
            cwd=working_dir,
            env=safe_env,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-102400:],
            "stderr": result.stderr[-102400:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": "Command timed out"}
    except OSError as exc:
        return {"ok": False, "returncode": -1, "stdout": "", "stderr": str(exc)}

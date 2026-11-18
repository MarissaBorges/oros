"""Read-only Arch Linux health and maintenance sentry."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def _run(command: list[str], timeout: int = 20) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {"ok": result.returncode == 0, "stdout": result.stdout[-10000:], "stderr": result.stderr[-2000:], "returncode": result.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "returncode": -1}


def disk_usage() -> dict:
    result = _run(["df", "-B1", "--output=target,size,used,avail,pcent", "/"])
    if not result["ok"]:
        return {"ok": False, "error": result["stderr"]}
    lines = [line.split() for line in result["stdout"].strip().splitlines()[1:] if line.strip()]
    if not lines:
        return {"ok": False, "error": "Unexpected df output"}
    target, size, used, available, percent = lines[0]
    return {
        "ok": True,
        "target": target,
        "size_bytes": int(size),
        "used_bytes": int(used),
        "available_bytes": int(available),
        "percent": percent,
    }


def failed_services(limit: int = 20) -> dict:
    result = _run(["systemctl", "--failed", "--no-pager", "--plain"], timeout=10)
    return {
        "ok": result["ok"],
        "services": [line for line in result["stdout"].splitlines() if ".service" in line][:limit],
        "error": result["stderr"] if not result["ok"] else "",
    }


def recent_journal(limit: int = 30) -> dict:
    result = _run(["journalctl", "-p", "warning", "-b", "-n", str(limit), "--no-pager", "-o", "short-iso"], timeout=20)
    return {
        "ok": result["ok"],
        "entries": [line for line in result["stdout"].splitlines() if line.strip()],
        "error": result["stderr"] if not result["ok"] else "",
    }


def package_state() -> dict:
    checkupdates = shutil.which("checkupdates")
    pending = _run([checkupdates], timeout=30) if checkupdates else {"ok": False, "stdout": "", "stderr": "checkupdates unavailable"}
    orphaned = _run(["pacman", "-Qdt"], timeout=20)
    return {
        "ok": True,
        "updates": [line for line in pending["stdout"].splitlines() if line.strip()],
        "updates_available": pending["ok"] and bool(pending["stdout"].strip()),
        "orphaned_packages": [line for line in orphaned["stdout"].splitlines() if line.strip()],
        "checkupdates_error": pending["stderr"] if not pending["ok"] else "",
    }


def snapshot() -> dict:
    disk = disk_usage()
    failed = failed_services()
    journal = recent_journal()
    packages = package_state()
    warnings = []
    if disk["ok"] and int(disk["percent"].rstrip("%")) >= 85:
        warnings.append("Disk usage is above 85 percent")
    if failed["services"]:
        warnings.append(f"{len(failed['services'])} failed system services")
    if packages["updates_available"]:
        warnings.append(f"{len(packages['updates'])} package updates available")
    if packages["orphaned_packages"]:
        warnings.append(f"{len(packages['orphaned_packages'])} orphaned packages")
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(),
        "disk": disk,
        "failed_services": failed,
        "journal": journal,
        "packages": packages,
        "warnings": warnings,
    }

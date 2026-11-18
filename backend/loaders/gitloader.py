"""Clone public GitHub repositories for local RAG indexing."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def download_repo(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != "github.com":
        raise ValueError("Only public github.com repositories are supported")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("Invalid GitHub repository URL")
    owner, repo = parts[:2]
    repo = repo.removesuffix(".git")
    root = Path(__file__).resolve().parents[2] / "data" / "repos" / f"{owner}-{repo}"
    root.parent.mkdir(parents=True, exist_ok=True)
    clone_url = f"https://github.com/{owner}/{repo}.git"
    if root.exists():
        shutil.rmtree(root)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, str(root)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Repository clone failed")
    return {"owner": owner, "repo": repo, "path": str(root)}

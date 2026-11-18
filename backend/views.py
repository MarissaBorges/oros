import json
import mimetypes
import os
import json
import sqlite3
import time
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .loaders.gitloader import download_repo
from .loaders.scraper import scraper_docs

from .rag import ask_huggingface, build_prompt, search_sources
from .desktop import active_windows, capture_screen, find_window, focus_window, open_url
from .shell import run_command
from .vault import Vault, VaultError
from .browser import find_chrome_debug_sessions, navigate_existing_browser
from .guardian import Guardian
from .context import snapshot as context_snapshot
from .sentinel import snapshot as sentinel_snapshot
from .warroom import start_war_room
from .research import search as research_search, extract as research_extract, create_report


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
executor = ThreadPoolExecutor(max_workers=2)
CONFIG_PATH = ROOT / "config" / "oros.json"
CHAT_DB = ROOT / "data" / "chat-history.sqlite3"


def _config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _vault():
    return Vault(_config()["vault"])


def _chat_db():
    CHAT_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CHAT_DB)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            payload TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    """)
    return connection


def frontend(request):
    return FileResponse(open(FRONTEND / "index.html", "rb"), content_type="text/html; charset=utf-8")


def frontend_asset(request, asset):
    path = (FRONTEND / asset).resolve()
    if FRONTEND not in path.parents or not path.is_file():
        return HttpResponse(status=404)
    content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return FileResponse(open(path, "rb"), content_type=content_type)


def status(request):
    sources = search_sources("documentation", limit=1000)
    collections = list((ROOT / "data" / "collections").glob("*/"))
    repos = list((ROOT / "data" / "repos").glob("*/"))
    return JsonResponse({"ok": True, "source_count": len(sources), "collections": [p.name for p in collections], "repositories": [p.name for p in repos], "hf_configured": bool(os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY"))})


def capabilities_status(request):
    config = _config()
    return JsonResponse({
        "ok": True,
        "runtime": "OpenJarvis",
        "runtime_source": str(ROOT / "vendor" / "OpenJarvis"),
        "vault": config["vault"],
        "browser_mode": config["browser_mode"],
        "autonomy": config["autonomy"],
        "desktop": "Hyprland",
        "active_windows": active_windows(),
    })


@csrf_exempt
def screen_capture(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    result = capture_screen(_config()["capture_dir"])
    if not result["ok"]:
        return JsonResponse(result, status=503)
    result.pop("base64", None)
    result["download_url"] = "/api/capabilities/screen/image"
    return JsonResponse(result)


def screen_image(request):
    path = Path(_config()["capture_dir"]) / "screen.png"
    if not path.is_file():
        return HttpResponse(status=404)
    return FileResponse(open(path, "rb"), content_type="image/png")


@csrf_exempt
def desktop_windows(request):
    if request.method != "GET":
        return JsonResponse({"error": "Use GET."}, status=405)
    return JsonResponse({"ok": True, "windows": active_windows()})


@csrf_exempt
def desktop_open(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    url = str(payload.get("url", "")).strip()
    if not url:
        return JsonResponse({"error": "URL is required."}, status=400)
    guardian = Guardian()
    authorization = guardian.authorize("open browser", url)
    if not authorization["allowed"]:
        return JsonResponse({"ok": False, "requires_approval": True, "approval": authorization}, status=202)
    existing = find_window(str(payload.get("match", ""))) if payload.get("match") else None
    if existing:
        focus_result = focus_window(existing["address"])
        if focus_result["ok"]:
            open_result = open_url(url)
            return JsonResponse({"ok": True, "existing_window": existing, "focused": True, "open": open_result})
    return JsonResponse({"ok": True, "existing_window": None, "open": open_url(url)})


def browser_sessions(request):
    return JsonResponse({"ok": True, "sessions": find_chrome_debug_sessions()})


@csrf_exempt
def browser_navigate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    url = str(payload.get("url", "")).strip()
    port = payload.get("port")
    if not url:
        return JsonResponse({"error": "URL is required."}, status=400)
    if port:
        result = navigate_existing_browser(int(port), url)
    else:
        import webbrowser
        webbrowser.open(url)
        result = {"ok": True, "url": url, "title": ""}
    return JsonResponse(result, status=200 if result["ok"] else 400)


@csrf_exempt
def guardian_requests(request):
    guardian = Guardian()
    if request.method == "GET":
        return JsonResponse({"ok": True, "pending": guardian.pending(), "audit": guardian.audit()})
    if request.method != "POST":
        return JsonResponse({"error": "Use GET or POST."}, status=405)
    payload = _json(request)
    action = str(payload.get("action", "")).strip()
    resource = str(payload.get("resource", "")).strip()
    approved = bool(payload.get("approved", False))
    if not action:
        return JsonResponse({"error": "Action is required."}, status=400)
    return JsonResponse({"ok": True, **guardian.authorize(action, resource, approved=approved, reason=str(payload.get("reason", "")))})


@csrf_exempt
def guardian_approve(request, record_id):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    return JsonResponse(Guardian().approve(record_id))


def context_active(request):
    return JsonResponse(context_snapshot())


def sentinel_status(request):
    return JsonResponse(sentinel_snapshot())


@csrf_exempt
def war_room(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    project = str(payload.get("project", "")).strip()
    note = str(payload.get("note", ""))
    if not project:
        return JsonResponse({"error": "Project path is required."}, status=400)
    return JsonResponse(start_war_room(project, note))


@csrf_exempt
def vault_graph(request):
    try:
        return JsonResponse(_vault().graph())
    except (VaultError, OSError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
def vault_garden(request):
    try:
        return JsonResponse(_vault().daily_garden())
    except (VaultError, OSError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
def vault_frontmatter(request):
    path = str(request.GET.get("path", "")).strip()
    if not path:
        return JsonResponse({"error": "path is required."}, status=400)
    try:
        return JsonResponse(_vault().frontmatter(path))
    except (VaultError, OSError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
def research(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    query = str(payload.get("query", "")).strip()
    if not query:
        return JsonResponse({"error": "Research query is required."}, status=400)
    try:
        results = research_search(query, int(payload.get("max_results", 8)))
        extracted = []
        for result in results[: min(5, len(results))]:
            try:
                item = research_extract(result["url"])
                if item["ok"]:
                    extracted.append(item)
            except Exception:
                continue
        report = None
        if payload.get("save_to_vault", True):
            report = create_report(query, results, _vault().root)
        return JsonResponse({"ok": True, "query": query, "results": results, "extracted": extracted, "report": report})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=502)


@csrf_exempt
def code_task(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    project = str(payload.get("project", "")).strip()
    command = str(payload.get("command", "")).strip()
    task = str(payload.get("task", "")).strip()
    if not project:
        return JsonResponse({"error": "Project path is required."}, status=400)
    project_path = Path(project).expanduser().resolve()
    if not project_path.is_dir():
        return JsonResponse({"error": "Project directory does not exist."}, status=400)
    if not any(project_path == Path(item).resolve() or project_path.is_relative_to(Path(item).resolve()) for item in _config()["allowed_shell_dirs"]):
        return JsonResponse({"error": "Project is outside the OROS allowlist."}, status=403)
    if not command:
        if (project_path / "pyproject.toml").exists():
            command = "python -m pytest -q"
        elif (project_path / "package.json").exists():
            command = "npm test -- --run"
        elif (project_path / "Cargo.toml").exists():
            command = "cargo test"
        elif (project_path / "go.mod").exists():
            command = "go test ./..."
        else:
            return JsonResponse({"error": "No test command could be inferred."}, status=400)
    guardian = Guardian()
    authorization = guardian.authorize(f"run {task or command}", str(project_path))
    if not authorization["allowed"]:
        return JsonResponse({"ok": False, "requires_approval": True, "approval": authorization}, status=202)
    return JsonResponse({"ok": True, "project": str(project_path), "command": command, **run_command(command, str(project_path), int(payload.get("timeout", 300)))})


def google_status(request):
    openjarvis_config = Path.home() / ".openjarvis"
    connectors = openjarvis_config / "connectors"
    available = []
    if connectors.exists():
        available = sorted(path.stem for path in connectors.glob("*.json"))
    return JsonResponse({
        "ok": True,
        "configured_connectors": available,
        "supported": ["gmail", "gcalendar", "gdrive", "gcontacts", "gtasks"],
        "setup": "Use 'jarvis connect gdrive' or the OpenJarvis connector UI.",
    })


@csrf_exempt
def vault_notes(request):
    if request.method != "GET":
        return JsonResponse({"error": "Use GET."}, status=405)
    directory = str(request.GET.get("directory", "")).strip()
    query = str(request.GET.get("query", "")).strip()
    try:
        vault = _vault()
        payload = vault.search(query) if query else vault.list_notes(directory)
        return JsonResponse({"ok": True, "notes": payload})
    except (VaultError, OSError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
def vault_note(request):
    relative_path = str(request.GET.get("path", "")).strip()
    try:
        vault = _vault()
        if request.method == "GET":
            if not relative_path:
                return JsonResponse({"error": "path is required."}, status=400)
            return JsonResponse({"ok": True, **vault.read(relative_path)})
        if request.method not in {"POST", "PUT", "DELETE"}:
            return JsonResponse({"error": "Use GET, POST, PUT or DELETE."}, status=405)
        payload = _json(request)
        if request.method == "DELETE":
            if not relative_path:
                return JsonResponse({"error": "path is required."}, status=400)
            authorization = Guardian().authorize("delete vault note", relative_path, approved=bool(payload.get("approved", False)))
            if not authorization["allowed"]:
                return JsonResponse({"ok": False, "requires_approval": True, "approval": authorization}, status=202)
            return JsonResponse({"ok": True, **vault.delete(relative_path)})
        relative_path = str(payload.get("path", relative_path)).strip()
        content = str(payload.get("content", ""))
        mode = str(payload.get("mode", "write"))
        if not relative_path:
            return JsonResponse({"error": "path is required."}, status=400)
        return JsonResponse({"ok": True, **vault.write(relative_path, content, mode)})
    except (VaultError, OSError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
def terminal_run(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    command = str(payload.get("command", "")).strip()
    working_dir = str(payload.get("working_dir", "/home/borges/dev")).strip()
    timeout = int(payload.get("timeout", 60))
    approved = bool(payload.get("approved", False))
    guardian = Guardian()
    authorization = guardian.authorize(f"run {command}", working_dir, approved=approved)
    if not authorization["allowed"]:
        return JsonResponse({"ok": False, "requires_approval": True, "approval": authorization}, status=202)
    return JsonResponse(run_command(command, working_dir, timeout))


@csrf_exempt
def project_snapshot(request):
    dev_root = Path("/home/borges/dev")
    projects = []
    for path in sorted(dev_root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not path.is_dir() or path.name.startswith("."):
            continue
        is_git = (path / ".git").exists()
        language = ""
        indicators = {
            "Python": ("pyproject.toml", "requirements.txt", "manage.py"),
            "JavaScript": ("package.json",),
            "Django": ("manage.py",),
            "Rust": ("Cargo.toml",),
            "Go": ("go.mod",),
        }
        matches = [name for name, files in indicators.items() if any((path / file).exists() for file in files)]
        language = matches[0] if matches else ""
        try:
            branch = subprocess.run(
                ["git", "-C", str(path), "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip() if is_git else ""
        except (OSError, subprocess.TimeoutExpired):
            branch = ""
        projects.append({
            "name": path.name,
            "path": str(path),
            "git": is_git,
            "branch": branch,
            "language": language,
            "modified": path.stat().st_mtime,
        })
    return JsonResponse({"ok": True, "projects": projects[:60]})


@csrf_exempt
def chat_history(request):
    connection = _chat_db()
    try:
        if request.method == "GET":
            rows = connection.execute(
                "SELECT id,title,created_at,updated_at FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
            return JsonResponse({
                "ok": True,
                "conversations": [
                    {"id": row[0], "title": row[1], "created_at": row[2], "updated_at": row[3]}
                    for row in rows
                ],
            })
        if request.method != "POST":
            return JsonResponse({"error": "Use GET or POST."}, status=405)
        payload = _json(request)
        conversation_id = payload.get("conversation_id")
        title = str(payload.get("title", "Nova conversa")).strip() or "Nova conversa"
        now = time.time()
        if conversation_id:
            conversation_id = int(conversation_id)
            connection.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (now, conversation_id),
            )
        else:
            cursor = connection.execute(
                "INSERT INTO conversations(title,created_at,updated_at) VALUES(?,?,?)",
                (title, now, now),
            )
            conversation_id = cursor.lastrowid
        connection.commit()
        return JsonResponse({"ok": True, "conversation_id": conversation_id})
    finally:
        connection.close()


@csrf_exempt
def conversation_detail(request, conversation_id):
    connection = _chat_db()
    try:
        if request.method == "GET":
            conversation = connection.execute(
                "SELECT id,title,created_at,updated_at FROM conversations WHERE id=?",
                (conversation_id,),
            ).fetchone()
            if not conversation:
                return JsonResponse({"error": "Conversation not found."}, status=404)
            messages = connection.execute(
                "SELECT id,role,content,payload,created_at FROM messages "
                "WHERE conversation_id=? ORDER BY id",
                (conversation_id,),
            ).fetchall()
            return JsonResponse({
                "ok": True,
                "conversation": {
                    "id": conversation[0],
                    "title": conversation[1],
                    "created_at": conversation[2],
                    "updated_at": conversation[3],
                },
                "messages": [
                    {
                        "id": row[0],
                        "role": row[1],
                        "content": row[2],
                        "payload": json.loads(row[3]) if row[3] else None,
                        "created_at": row[4],
                    }
                    for row in messages
                ],
            })
        if request.method != "POST":
            return JsonResponse({"error": "Use GET or POST."}, status=405)
        payload = _json(request)
        role = str(payload.get("role", "")).strip()
        content = str(payload.get("content", "")).strip()
        if role not in {"user", "assistant", "system"} or not content:
            return JsonResponse({"error": "Valid role and content are required."}, status=400)
        now = time.time()
        connection.execute(
            "INSERT INTO messages(conversation_id,role,content,payload,created_at) "
            "VALUES(?,?,?,?,?)",
            (
                conversation_id,
                role,
                content,
                json.dumps(payload.get("payload"), ensure_ascii=False) if payload.get("payload") is not None else None,
                now,
            ),
        )
        connection.execute(
            "UPDATE conversations SET updated_at=? WHERE id=?",
            (now, conversation_id),
        )
        if role == "user":
            title = content[:48].replace("\n", " ")
            connection.execute(
                "UPDATE conversations SET title=? WHERE id=? AND title='Nova conversa'",
                (title, conversation_id),
            )
        connection.commit()
        return JsonResponse({"ok": True})
    finally:
        connection.close()


def _json(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}


@csrf_exempt
def chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    question = str(payload.get("message", "")).strip()
    if not question:
        return JsonResponse({"error": "A mensagem é obrigatória."}, status=400)
    sources = search_sources(question)
    prompt = build_prompt(question, payload.get("history", []), sources)
    answer, error = ask_huggingface(prompt)
    steps = [
        {"label": "Entendi a pergunta", "detail": f"Identifiquei o objetivo técnico e {len(question.split())} palavras-chave."},
        {"label": "Busquei na base local", "detail": f"Comparei os documentos indexados e encontrei {len(sources)} fonte(s) relevante(s)."},
        {"label": "Selecionei evidências", "detail": "Priorizei os trechos com maior sobreposição semântica com a pergunta."},
        {"label": "Preparei a resposta", "detail": "A resposta foi sintetizada pelo modelo usando apenas o contexto recuperado."},
    ]
    if error:
        answer = "Ainda não consigo consultar o modelo de IA. " + error
        steps[-1]["detail"] = "A recuperação funcionou, mas a chamada ao modelo não foi concluída."
    citations = [{"title": item["title"], "path": item["path"], "url": item.get("url") or None, "score": item["score"]} for item in sources]
    result = {"answer": answer, "steps": steps, "sources": citations, "model": os.getenv("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct"), "error": error}
    conversation_id = payload.get("conversation_id")
    if conversation_id:
        connection = _chat_db()
        try:
            now = time.time()
            connection.execute(
                "INSERT INTO messages(conversation_id,role,content,payload,created_at) "
                "VALUES(?,?,?,?,?)",
                (conversation_id, "user", question, None, now),
            )
            connection.execute(
                "INSERT INTO messages(conversation_id,role,content,payload,created_at) "
                "VALUES(?,?,?,?,?)",
                (conversation_id, "assistant", answer, json.dumps(result, ensure_ascii=False), now + 0.001),
            )
            connection.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (now, conversation_id),
            )
            connection.execute(
                "UPDATE conversations SET title=? WHERE id=? AND title='Nova conversa'",
                (question[:48].replace("\n", " "), conversation_id),
            )
            connection.commit()
            result["conversation_id"] = int(conversation_id)
        except sqlite3.Error:
            pass
        finally:
            connection.close()
    return JsonResponse(result)


@csrf_exempt
def ingest_docs(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    url = str(payload.get("url", "")).strip()
    if not url:
        return JsonResponse({"error": "Informe a URL da documentação."}, status=400)
    collection = str(payload.get("collection", "docs")).strip() or "docs"
    future = executor.submit(scraper_docs, nome_colecao=collection, url=url, versao=payload.get("version") or None, acessar_links_internos=bool(payload.get("follow_links", True)), batch_size=int(payload.get("batch_size", 10)), profundidade=int(payload.get("depth", 10)))
    return JsonResponse({"queued": True, "collection": collection, "message": "Coleta iniciada. O conteúdo ficará disponível para o chat ao terminar."}, status=202)


@csrf_exempt
def ingest_repo(request):
    if request.method != "POST":
        return JsonResponse({"error": "Use POST."}, status=405)
    payload = _json(request)
    url = str(payload.get("url", "")).strip()
    if not url.startswith(("https://github.com/", "http://github.com/")):
        return JsonResponse({"error": "Informe uma URL pública do GitHub."}, status=400)
    executor.submit(download_repo, url)
    return JsonResponse({"queued": True, "message": "Repositório adicionado à fila de indexação."}, status=202)

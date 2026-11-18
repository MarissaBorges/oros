from django.urls import path

from . import views


urlpatterns = [
    path("", views.frontend, name="frontend"),
    path("api/status", views.status, name="status"),
    path("api/capabilities/status", views.capabilities_status, name="capabilities-status"),
    path("api/capabilities/screen/capture", views.screen_capture, name="screen-capture"),
    path("api/capabilities/screen/image", views.screen_image, name="screen-image"),
    path("api/capabilities/windows", views.desktop_windows, name="desktop-windows"),
    path("api/capabilities/open", views.desktop_open, name="desktop-open"),
    path("api/browser/sessions", views.browser_sessions, name="browser-sessions"),
    path("api/browser/navigate", views.browser_navigate, name="browser-navigate"),
    path("api/vault/notes", views.vault_notes, name="vault-notes"),
    path("api/vault/note", views.vault_note, name="vault-note"),
    path("api/terminal/run", views.terminal_run, name="terminal-run"),
    path("api/context/active", views.context_active, name="context-active"),
    path("api/sentinel/status", views.sentinel_status, name="sentinel-status"),
    path("api/war-room", views.war_room, name="war-room"),
    path("api/guardian", views.guardian_requests, name="guardian"),
    path("api/guardian/<str:record_id>/approve", views.guardian_approve, name="guardian-approve"),
    path("api/vault/graph", views.vault_graph, name="vault-graph"),
    path("api/vault/garden", views.vault_garden, name="vault-garden"),
    path("api/vault/frontmatter", views.vault_frontmatter, name="vault-frontmatter"),
    path("api/research", views.research, name="research"),
    path("api/code/task", views.code_task, name="code-task"),
    path("api/google/status", views.google_status, name="google-status"),
    path("api/projects", views.project_snapshot, name="projects"),
    path("api/chat/history", views.chat_history, name="chat-history"),
    path("api/chat/history/<int:conversation_id>", views.conversation_detail, name="conversation-detail"),
    path("api/chat", views.chat, name="chat"),
    path("api/ingest/docs", views.ingest_docs, name="ingest-docs"),
    path("api/ingest/repo", views.ingest_repo, name="ingest-repo"),
    path("<path:asset>", views.frontend_asset, name="frontend-asset"),
]

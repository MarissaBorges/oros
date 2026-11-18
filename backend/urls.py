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
    path("api/vault/notes", views.vault_notes, name="vault-notes"),
    path("api/vault/note", views.vault_note, name="vault-note"),
    path("api/terminal/run", views.terminal_run, name="terminal-run"),
    path("api/chat", views.chat, name="chat"),
    path("api/ingest/docs", views.ingest_docs, name="ingest-docs"),
    path("api/ingest/repo", views.ingest_repo, name="ingest-repo"),
    path("<path:asset>", views.frontend_asset, name="frontend-asset"),
]

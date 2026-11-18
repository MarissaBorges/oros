import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

from django.test import Client


def test_projects_endpoint() -> None:
    response = Client().get("/api/projects")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "projects" in payload


def test_chat_history_create_and_detail() -> None:
    client = Client()
    created = client.post(
        "/api/chat/history",
        data={"title": "Teste OROS"},
        content_type="application/json",
    )
    assert created.status_code == 200
    conversation_id = created.json()["conversation_id"]

    saved = client.post(
        f"/api/chat/history/{conversation_id}",
        data={"role": "user", "content": "Olá, OROS"},
        content_type="application/json",
    )
    assert saved.status_code == 200

    detail = client.get(f"/api/chat/history/{conversation_id}")
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["content"] == "Olá, OROS"


def test_vault_notes_endpoint() -> None:
    response = Client().get("/api/vault/notes")
    assert response.status_code == 200
    assert response.json()["ok"] is True

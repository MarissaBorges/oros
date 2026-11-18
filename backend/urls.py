from django.urls import path

from . import views


urlpatterns = [
    path("", views.frontend, name="frontend"),
    path("api/status", views.status, name="status"),
    path("api/chat", views.chat, name="chat"),
    path("api/ingest/docs", views.ingest_docs, name="ingest-docs"),
    path("api/ingest/repo", views.ingest_repo, name="ingest-repo"),
    path("<path:asset>", views.frontend_asset, name="frontend-asset"),
]

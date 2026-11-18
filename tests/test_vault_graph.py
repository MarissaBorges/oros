from pathlib import Path

from backend.vault import Vault


def test_vault_graph_wikilinks(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.write("Projetos/OROS.md", "# OROS\nVeja [[Arquitetura]]")
    vault.write("Arquitetura.md", "# Arquitetura")
    graph = vault.graph()
    assert any(edge["source"] == "Projetos/OROS" and edge["target"] == "Arquitetura" for edge in graph["edges"])

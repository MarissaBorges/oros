from pathlib import Path

import pytest

from backend.vault import Vault, VaultError


def test_vault_search_and_write(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.write("Projetos/OROS.md", "# OROS\nAssistente autônomo local")

    assert vault.read("Projetos/OROS.md")["content"].startswith("# OROS")
    assert vault.search("assistente local")[0]["path"] == "Projetos/OROS.md"


def test_vault_rejects_parent_traversal(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    with pytest.raises(VaultError):
        vault.read("../outside.md")


def test_vault_append_and_trash(tmp_path: Path) -> None:
    vault = Vault(tmp_path)
    vault.write("Inbox.md", "Primeira linha\n")
    vault.write("Inbox.md", "\nSegunda linha\n", mode="append")

    assert "Segunda linha" in vault.read("Inbox.md")["content"]
    result = vault.delete("Inbox.md")
    assert result["deleted"] == "Inbox.md"
    assert not (tmp_path / "Inbox.md").exists()

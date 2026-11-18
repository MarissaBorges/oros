from pathlib import Path

from backend.guardian import Guardian


def test_guardian_read_is_free(tmp_path: Path) -> None:
    result = Guardian(tmp_path / "guardian.sqlite3").authorize("read vault note", "00 Entrada/Test.md")
    assert result["risk_level"] == 0
    assert result["allowed"] is True


def test_guardian_destructive_action_requires_approval(tmp_path: Path) -> None:
    guardian = Guardian(tmp_path / "guardian.sqlite3")
    pending = guardian.authorize("delete vault note", "00 Entrada/Test.md")
    assert pending["risk_level"] == 2
    assert pending["allowed"] is False
    assert pending["status"] == "pending"

    approved = guardian.approve(pending["id"])
    assert approved["ok"] is True
    assert guardian.pending() == []

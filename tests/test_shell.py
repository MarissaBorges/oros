from backend.shell import is_allowed_directory, validate_command


def test_shell_blocks_destructive_patterns() -> None:
    assert validate_command("rm -rf /") is not None
    assert validate_command("shutdown now") is not None
    assert validate_command("pytest -q") is None


def test_shell_directory_allowlist() -> None:
    assert is_allowed_directory("/home/borges/dev/oros", ["/home/borges/dev"])
    assert not is_allowed_directory("/etc", ["/home/borges/dev"])

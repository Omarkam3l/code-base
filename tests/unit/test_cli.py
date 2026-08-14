"""Unit tests for CodeGraph CLI commands."""

from codegraph.cli.main import CodeGraphCLI


def test_cli_subcommands_dispatch() -> None:
    cli = CodeGraphCLI()

    assert cli.run(["index", "."]) == 0
    assert cli.run(["ask", "Where is UserService defined?"]) == 0
    assert cli.run(["investigate", "Why authentication failed?"]) == 0
    assert cli.run(["impact", "UserService"]) == 0
    assert cli.run(["dependencies", "UserService"]) == 0
    assert cli.run(["trace", "tr_12345"]) == 0
    assert cli.run(["change", "Refactor UserService"]) == 0
    assert cli.run(["repair"]) == 0
    assert cli.run(["pr"]) == 0
    assert cli.run(["evaluate"]) == 0

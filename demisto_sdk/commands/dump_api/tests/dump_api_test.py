import typer
from typer.main import get_command

import demisto_sdk.__main__ as sdk_main


def test_export_api_registers_all_commands(monkeypatch):
    """
    Given: The user invokes the `export-api` command.
    When:  `register_commands` is called with ["export-api"].
    Then:  All SDK commands are registered on `app` (not just `export-api`),
           so that the resulting dump contains the full API surface.
    """
    # Use a fresh app, since the global one is already populated by conftest.
    fresh_app = typer.Typer()
    monkeypatch.setattr(sdk_main, "app", fresh_app)

    sdk_main.register_commands(["export-api"])

    command_names = set(get_command(fresh_app).commands.keys())  # type: ignore[attr-defined]

    assert "export-api" in command_names
    assert {"upload", "download", "validate", "format"}.issubset(command_names)
    assert len(command_names) > 5

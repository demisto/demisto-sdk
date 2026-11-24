"""Sample: commands dispatched through dict keys (E9010, E9011)."""

PREFIX = "vendor"
SEARCH = "search-command"


def main() -> None:
    commands = {
        "test-module": test_module,
        "dict-a": command_a,
        SEARCH: search,
        f"{PREFIX}-dict-b": command_b,
        f"static-dict-fstring": command_c,
        **extra_commands,
    }
    other_mapping = {1: "one", "dict-value-only": "dict-in-value"}
    command = demisto.command()
    if command in commands:
        return_results(commands[command]())

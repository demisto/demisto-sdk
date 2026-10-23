"""Sample: command names coming from function arguments and reassigned variables."""


def dispatch(command: str, name: str) -> None:
    if command == name:
        pass


def main() -> None:
    target = "first-value"
    target = "second-value"
    command = demisto.command()
    if command == target:
        pass
    if command == "test-module":
        pass

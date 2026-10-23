"""Sample: commands dispatched with if / elif / in / or (E9010, E9011)."""

PREFIX = "xdr"
FETCH_COMMAND = "fetch-incidents"
ALIASES = ("alias-one", "alias-two")


def main() -> None:
    command = demisto.command()
    if command == "test-module":
        pass
    elif command == "eq-command":
        pass
    elif "reversed-command" == command:
        pass
    elif command in ["list-a", "list-b"]:
        pass
    elif command in ("tuple-a", "tuple-b"):
        pass
    elif command in {"set-a", "set-b"}:
        pass
    elif command == "or-a" or command == "or-b":
        pass
    elif command == FETCH_COMMAND:
        pass
    elif command == f"{PREFIX}-get-alert":
        pass
    elif command == f"static-fstring":
        pass
    elif command in ALIASES:
        pass
    elif command != "not-equal-command":
        pass
    elif command.startswith("prefix-"):
        pass
    else:
        raise NotImplementedError(command)

    if command == "after-else":
        pass
    else:
        print("else body")
        if command == "nested-in-else":
            pass


def other() -> None:
    if demisto.command() == "outside-main":
        pass
    match demisto.command():
        case "match-command":
            pass

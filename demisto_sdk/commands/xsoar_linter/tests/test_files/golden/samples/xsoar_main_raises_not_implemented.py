"""Sample: main raises NotImplementedError(...) for unknown commands (W9018 satisfied)."""


def main() -> None:
    command = demisto.command()
    try:
        if command == "test-module":
            return_results("ok")
        else:
            raise NotImplementedError(f"Command {command} is not implemented")
    except Exception as e:
        return_error(str(e))

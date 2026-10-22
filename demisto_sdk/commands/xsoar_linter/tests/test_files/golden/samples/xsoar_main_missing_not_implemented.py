"""Sample: main never raises NotImplementedError (W9018)."""


def main() -> None:
    command = demisto.command()
    try:
        if command == "test-module":
            return_results("ok")
        else:
            raise ValueError(f"Unknown command {command}")
    except Exception as e:
        return_error(str(e))

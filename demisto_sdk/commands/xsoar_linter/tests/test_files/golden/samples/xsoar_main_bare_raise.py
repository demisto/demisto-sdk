"""Sample: main contains a bare raise and no NotImplementedError."""


def main() -> None:
    command = demisto.command()
    try:
        if command == "test-module":
            return_results("ok")
    except Exception:
        raise

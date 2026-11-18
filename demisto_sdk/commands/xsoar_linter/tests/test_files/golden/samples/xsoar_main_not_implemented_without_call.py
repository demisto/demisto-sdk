"""Sample: main raises NotImplementedError without calling it."""


def main() -> None:
    command = demisto.command()
    try:
        if command == "test-module":
            return_results("ok")
        else:
            raise NotImplementedError
    except Exception as e:
        return_error(str(e))

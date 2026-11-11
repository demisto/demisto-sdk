"""Sample: a main function with try/except and a single return_error."""


def main() -> None:
    try:
        run()
    except Exception as e:
        return_error(str(e))

"""Sample: main with try/finally and no return_error (W9012)."""


def main() -> None:
    try:
        run()
    finally:
        cleanup()

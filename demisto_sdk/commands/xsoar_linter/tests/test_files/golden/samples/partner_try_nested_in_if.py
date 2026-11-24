"""Sample: try/except nested inside an if in main (W9010 looks only at top-level statements)."""


def main() -> None:
    if ready:
        try:
            run()
        except Exception as e:
            return_error(str(e))

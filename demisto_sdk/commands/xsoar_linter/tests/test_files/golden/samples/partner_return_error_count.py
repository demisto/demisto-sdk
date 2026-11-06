"""Sample: return_error used more than once (W9011)."""


def helper() -> None:
    return_error("helper failed")
    CommonServerPython.return_error("attribute call")


def main() -> None:
    try:
        run()
    except Exception:
        return_error("failed")

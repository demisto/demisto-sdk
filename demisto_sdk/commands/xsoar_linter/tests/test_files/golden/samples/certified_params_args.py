"""Sample: demisto.params() / demisto.args() inside and outside main (W9016, W9017)."""

PARAMS = demisto.params()
ARGS = demisto.args()


def helper() -> dict:
    return demisto.args()


class Client:
    def __init__(self) -> None:
        self.params = demisto.params()


def main() -> None:
    params = demisto.params()
    args = demisto.args()

    def inner() -> dict:
        return demisto.params()

    handler = lambda: demisto.args()  # noqa: E731
    other.params()
    other.args()

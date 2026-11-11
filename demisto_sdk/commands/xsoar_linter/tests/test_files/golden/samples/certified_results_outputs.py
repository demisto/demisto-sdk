"""Sample: demisto.results and return_outputs calls (W9008, W9009)."""


def main() -> None:
    demisto.results("x")
    return_outputs("x")
    self.demisto.results("x")
    CommonServerPython.return_outputs("x")
    results("x")
    other.results("x")

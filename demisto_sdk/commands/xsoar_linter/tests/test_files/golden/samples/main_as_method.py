"""Sample: the only function named main is a class method."""


class Client:
    def main(self) -> None:
        demisto.params()


def run() -> None:
    pass

"""Sample: print calls (E9002)."""


def helper(value: str) -> None:
    print(value)


class Reporter:
    def print(self, value: str) -> None:
        self.print(value)


print("module level")
log_print = print
logger.print("attribute call named print")
print

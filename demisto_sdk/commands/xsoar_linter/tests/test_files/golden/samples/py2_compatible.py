"""Sample: code that is valid in both Python 2 and Python 3, used with the PY2 flag."""

PREFIX = "legacy"


def helper(value):
    return value


def main():
    commands = {
        "test-module": helper,
        "py2-dict-command": helper,
        PREFIX + "-concat-command": helper,
    }
    command = demisto.command()
    if command == "py2-if-command":
        pass
    print("py2 compatible print")

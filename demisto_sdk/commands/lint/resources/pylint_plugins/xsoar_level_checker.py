from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1

    def __init__(self, linter: PyLinter = None):
        super().__init__(linter)
        self.list_of_function_names: set = set()

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter) -> None:
    linter.register_checker(XsoarChecker(linter))

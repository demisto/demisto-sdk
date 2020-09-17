from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1

    def __init__(self, linter=None):
        super(XsoarChecker, self).__init__(linter)
        self.list_of_function_names = set()

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter):
    linter.register_checker(XsoarChecker(linter))

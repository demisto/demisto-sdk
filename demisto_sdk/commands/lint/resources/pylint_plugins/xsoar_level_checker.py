from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

xsoar_msg = {}  # type: ignore


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1
    msgs = xsoar_msg

    def __init__(self, linter=None):
        super(XsoarChecker, self).__init__(linter)
        self.list_of_function_names = set()

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter):
    linter.register_checker(XsoarChecker(linter))

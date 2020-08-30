from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class PartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "partner-checker"
    priority = -1

    def __init__(self, linter: PyLinter = None):
        super(PartnerChecker, self).__init__(linter)

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter) -> None:
    linter.register_checker(PartnerChecker(linter))

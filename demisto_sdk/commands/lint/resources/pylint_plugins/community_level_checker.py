from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class CommunityChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "community-checker"
    priority = -1

    def __init__(self, linter: PyLinter = None):
        super(CommunityChecker, self).__init__(linter)

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter) -> None:
    linter.register_checker(CommunityChecker(linter))

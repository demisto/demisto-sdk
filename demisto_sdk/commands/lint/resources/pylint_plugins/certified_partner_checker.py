from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class CertifiedPartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "community-checker"
    priority = -1

    def __init__(self, linter: PyLinter = None):
        super(CertifiedPartnerChecker, self).__init__(linter)

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter) -> None:
    linter.register_checker(CertifiedPartnerChecker(linter))

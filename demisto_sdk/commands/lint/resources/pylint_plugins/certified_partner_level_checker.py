from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker


class CertifiedPartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "community-checker"
    priority = -1

    def __init__(self, linter=None):
        super().__init__(linter)

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter):
    linter.register_checker(CertifiedPartnerChecker(linter))

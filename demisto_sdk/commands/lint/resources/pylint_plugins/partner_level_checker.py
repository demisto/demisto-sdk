from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

partner_msg = {'msg'}


class PartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "partner-checker"
    priority = -1
    msgs = partner_msg

    def __init__(self, linter=None):
        super(PartnerChecker, self).__init__(linter)

    # -------------------------------------------- Validations--------------------------------------------------


def register(linter):
    linter.register_checker(PartnerChecker(linter))

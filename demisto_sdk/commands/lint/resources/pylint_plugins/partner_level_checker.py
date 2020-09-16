from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

partner_msg: dict = {
    "W9006": ("try and except statements were not found in main function. Please add them", "try-except-main",
              "Ensure to not try except in the main function.",),
    "W9007": ("return.error should be used only once in the code, in main function. Please remove other usages.",
              "too-many-return-error",
              "return.error should be used only once in the code",),
}


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

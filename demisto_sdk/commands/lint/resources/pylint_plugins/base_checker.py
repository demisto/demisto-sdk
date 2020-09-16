import os

from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# You can find documentation about adding new checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker

base_msg = {
    "E9002": ("Print is found, Please remove all prints from the code.", "print-exists",
              "Please remove all prints from the code.",),
    "E9003": ("Sleep is found, Please remove all sleep statements from the code.", "sleep-exists",
              "Please remove all sleep statments from the code.",),
}


# -------------------------------------------- Messages for all linters ------------------------------------------------


class CustomBaseChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "base-checker"
    priority = -1
    msgs = base_msg

    def __init__(self, linter=None):
        super(CustomBaseChecker, self).__init__(linter)

    def visit_call(self, node):
        self._print_checker(node)
        self._sleep_checker(node)

    # Print statment for Python2 only.
    def visit_print(self, node):
        self.add_message("print-exists", node=node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _print_checker(self, node):
        try:
            if node.func.name == 'print':
                self.add_message("print-exists", node=node)
        except Exception:
            pass

    def _sleep_checker(self, node):
        if not os.getenv('LONGRUNNING'):
            try:
                if node.func.attrname == 'sleep' and node.func.expr.name == 'time':
                    self.add_message("sleep-exists", node=node)
            except Exception:
                try:
                    if node.func.name == 'sleep':
                        self.add_message("sleep-exists", node=node)
                except Exception:
                    pass


def register(linter):
    linter.register_checker(CustomBaseChecker(linter))

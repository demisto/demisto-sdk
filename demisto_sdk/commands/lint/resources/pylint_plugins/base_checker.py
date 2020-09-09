from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# You can find documentation about adding new checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker

Msg_XSOAR_linter = {
    'base_checker': {
        "E9001": ("Sys.exit use is found, Please use return instead.", "sys-exit-exists",
                  "Ensure to not use sys.exit in the code.",),
        "E9002": ("Print is found, Please remove all prints from the code.", "print-exists",
                  "Please remove all prints from the code.",)
    },
    'community_level_checker': {},
    'partner_level_checker': {},
    'certified_partner_level_checker': {},
    'xsoar_level_checker': {}
}


class CustomBaseChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "base-checker"
    priority = -1
    msgs = Msg_XSOAR_linter.get('base_checker')

    def __init__(self, linter=None):
        super(CustomBaseChecker, self).__init__(linter)

    def visit_call(self, node):
        self._sys_exit_checker(node)
        self._print_checker(node)

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

    def _sys_exit_checker(self, node):
        try:
            if node.func.attrname == 'exit' and node.func.expr.name == 'sys' and node.args and node.args[0].value != 0:
                self.add_message("sys-exit-exists", node=node)
        except Exception:
            pass


def register(linter):
    linter.register_checker(CustomBaseChecker(linter))

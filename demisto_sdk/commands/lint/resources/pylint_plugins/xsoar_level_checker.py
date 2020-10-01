from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

xsoar_msg = {
    "W9013": (
        "Docstrings was not found, Please add to function.", "docstring-doesnt-exits",
        "Ensure to not try except in the main function.",)
}


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1
    msgs = xsoar_msg

    def __init__(self, linter=None):
        super(XsoarChecker, self).__init__(linter)

    def visit_functiondef(self, node):
        self._docstring_checker(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _docstring_checker(self, node):
        if not node.doc and node.name != 'main':
            self.add_message("docstring-doesnt-exits", node=node)


def register(linter):
    linter.register_checker(XsoarChecker(linter))

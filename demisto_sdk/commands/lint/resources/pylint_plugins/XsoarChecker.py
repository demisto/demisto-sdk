# Pylint documentation for writing a checker: http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html
# This is an example of a Pylint AST checker and should not be registered to use
# In an AST (abstract syntax tree) checker, the code will be represented as nodes of a tree
# We will use the astroid library: https://astroid.readthedocs.io/en/latest/api/general.html to visit and leave nodes
# Libraries needed for an AST checker
from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker

    # Checker name
    name = "xsoar-checker"
    # Set priority to -1
    priority = -1
    # Message dictionary
    msgs = {
        # message-id, consists of a letter and numbers
        # Letter will be one of following letters (C=Convention, W=Warning, E=Error, F=Fatal, R=Refactoring)
        # Numbers need to be unique and in-between 9000-9999
        "E9003": (
            # displayed-message shown to user
            "Main function wasnt found in the file, Please add main()",
            # message-symbol used as alias for message-id
            "main-func-doesnt-exist",
            # message-help shown to user when calling pylint --help-msg
            "Please remove all prints from the code.",
        )
    }

    def __init__(self, linter: PyLinter = None):
        super().__init__(linter)
        self.list_of_function_names: set = set()

    def visit_functiondef(self, node: nodes):
        self.list_of_function_names.add(node.name)

    def leave_module(self, node):
        self._main_function(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _main_function(self, node):
        if 'main' not in self.list_of_function_names:
            self.add_message("main-func-doesnt-exist", node=node)


def register(linter) -> None:
    linter.register_checker(XsoarChecker(linter))

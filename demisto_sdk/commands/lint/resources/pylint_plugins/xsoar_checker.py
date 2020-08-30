from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1
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

    def visit_functiondef(self, node):
        self.list_of_function_names.add(node.name)

    def leave_module(self, node):
        self._main_function(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _main_function(self, node):
        if 'main' not in self.list_of_function_names:
            self.add_message("main-func-doesnt-exist", node=node)


def register(linter) -> None:
    linter.register_checker(XsoarChecker(linter))

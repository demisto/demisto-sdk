from astroid import nodes
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker
from pylint.lint import PyLinter


class CustomBaseChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "base-checker"
    priority = -1
    msgs = {
        "E9001": (
            # displayed-message shown to user
            "Sys.exit use is found, Please use return instead.",
            # message-symbol used as alias for message-id
            "sys-exit-exists",
            # message-help shown to user when calling pylint --help-msg
            "Ensure to not use sys.exit in the code.",
        ),
        "E9002": (
            # displayed-message shown to user
            "Print is found, Please remove all prints from the code.",
            # message-symbol used as alias for message-id
            "print-exists",
            # message-help shown to user when calling pylint --help-msg
            "Please remove all prints from the code.",
        ),
        "E9003": (
            # displayed-message shown to user
            "demisto.log is found, Please remove, you can choose to replace it with demisto.debug or logger",
            # message-symbol used as alias for message-id
            "demisto-log-exists",
            # message-help shown to user when calling pylint --help-msg
            "Please remove all demisto.log from the code.",
        ),
        "E9004": (
            # displayed-message shown to user
            "time.sleep is found, Please remove any sleep functionality from the code",
            # message-symbol used as alias for message-id
            "sleep-exists",
            # message-help shown to user when calling pylint --help-msg
            "Please remove all sleep functionality from the code.",
        )
    }

    def __init__(self, linter: PyLinter = None):
        super(CustomBaseChecker, self).__init__(linter)

    def visit_call(self, node: nodes) -> None:
        self._sys_exit_checker(node)
        self._print_checker(node)
        self._demisto_log_checker(node)
        self._sleep_checker(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _print_checker(self, node):
        try:
            if node.func.name == 'print':
                self.add_message("print-exists", node=node)
        except Exception:
            pass

    def _sys_exit_checker(self, node):
        try:
            if node.func.attrname == 'exit' and node.func.expr.name == 'sys':
                self.add_message("sys-exit-exists", node=node)
        except Exception:
            pass

    def _demisto_log_checker(self, node):
        try:
            if node.func.attrname == 'log' and node.func.expr.name == 'demisto':
                self.add_message("demisto-log-exists", node=node)
        except Exception:
            pass

    def _sleep_checker(self, node):
        try:
            if node.func.attrname == 'sleep' and node.func.expr.name == 'time':
                self.add_message("sleep-exists", node=node)
        except Exception:
            pass


def register(linter) -> None:
    linter.register_checker(CustomBaseChecker(linter))

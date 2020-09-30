from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

cert_partner_msg = {
    "E9001": ("Sys.exit use is found, Please use return instead.", "sys-exit-exists",
              "Ensure to not use sys.exit in the code.",),
    "W9004": ("Demisto.log is found, Please remove all demisto.log usage and exchange it with Logger/demisto.debug",
              "demisto-log-exists",
              "Please remove all demisto.log usage and exchange it with Logger/demisto.debug",),
    "W9005": ("Main function wasnt found in the file, Please add main()", "main-func-doesnt-exist",
              "Please remove all prints from the code.",),
    "W9008": (
        "Do not use demisto.results function. Please return CommandResults object instead.", "demisto-results-exists",
        "Do not use demisto.results function.",),
    "W9009": (
        "Do not use return_outputs function. Please return CommandResults object instead.", "return-outputs-exists",
        "Do not use return_outputs function.",),
    "W9014": (
        "Function arguments are missing type annotations. Please add type annotations",
        "args-type-annotations-doesnt-exist",
        "Function arguments are missing type annotations. Please add type annotations",),
    "W9015": (
        "Function return value type annotation is missing. Please add type annotations",
        "return-type-annotations-doesnt-exist",
        "Function return value type annotation is missing. Please add type annotations",),
}


class CertifiedPartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "certified-partner-checker"
    priority = -1
    msgs = cert_partner_msg

    def __init__(self, linter=None):
        super(CertifiedPartnerChecker, self).__init__(linter)
        self.list_of_function_names = set()

    def visit_call(self, node):
        self._sys_exit_checker(node)
        self._demisto_log_checker(node)
        self._return_outputs_checker(node)
        self._demisto_results_checker(node)

    def visit_functiondef(self, node):
        self.list_of_function_names.add(node.name)
        self._type_annotations_checker(node)

    def leave_module(self, node):
        self._main_function(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _sys_exit_checker(self, node):
        try:
            if node.func.attrname == 'exit' and node.func.expr.name == 'sys' and node.args and node.args[0].value != 0:
                self.add_message("sys-exit-exists", node=node)
        except Exception:
            pass

    def _demisto_log_checker(self, node):
        try:
            if node.func.attrname == 'log' and node.func.expr.name == 'demisto':
                self.add_message("demisto-log-exists", node=node)
        except Exception:
            pass

    def _main_function(self, node):
        if 'main' not in self.list_of_function_names:
            self.add_message("main-func-doesnt-exist", node=node)

    def _return_outputs_checker(self, node):
        try:
            if node.func.name == 'return_outputs':
                self.add_message("return-outputs-exists", node=node)
        except Exception:
            pass

    def _demisto_results_checker(self, node):
        try:
            if node.func.attrname == 'results' and node.func.expr.name == 'demisto':
                self.add_message("demisto-results-exists", node=node)
        except Exception:
            pass

    def _type_annotations_checker(self, node):
        annotation = True
        for ann, args in zip(node.args.annotations, node.args.args):
            if not ann and args.name != 'self':
                annotation = False
        if not annotation and node.name not in ['main', '__init__']:
            self.add_message("args-type-annotations-doesnt-exist", node=node)
        if not node.returns and node.name not in ['main', '__init__']:
            self.add_message("return-type-annotations-doesnt-exist", node=node)


def register(linter):
    linter.register_checker(CertifiedPartnerChecker(linter))

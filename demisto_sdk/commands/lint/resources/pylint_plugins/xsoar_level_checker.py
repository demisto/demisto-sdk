import os

from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

xsoar_msg = {
    "W9013": (
        "Docstrings was not found, Please add to function.", "docstring-doesnt-exits",
        "Ensure to not try except in the main function.",),
    "W9014": (
        "Function arguments are missing type annotations. Please add type annotations",
        "args-type-annotations-doesnt-exist",
        "Function arguments are missing type annotations. Please add type annotations",),
    "W9015": (
        "Function return value type annotation is missing. Please add type annotations",
        "return-type-annotations-doesnt-exist",
        "Function return value type annotation is missing. Please add type annotations",),
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
        self._type_annotations_checker(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _docstring_checker(self, node):
        if not node.doc and node.name != 'main':
            self.add_message("docstring-doesnt-exits", node=node)

    def _type_annotations_checker(self, node):
        if os.getenv('PY2'):
            annotation = True
            for ann, args in zip(node.args.annotations, node.args.args):
                if not ann and args.name != 'self':
                    annotation = False
            if not annotation and node.name not in ['main', '__init__']:
                self.add_message("args-type-annotations-doesnt-exist", node=node)
            if not node.returns and node.name not in ['main', '__init__']:
                self.add_message("return-type-annotations-doesnt-exist", node=node)


def register(linter):
    linter.register_checker(XsoarChecker(linter))

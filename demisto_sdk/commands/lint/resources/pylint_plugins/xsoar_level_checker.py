import os

import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

xsoar_msg = {
    "W9014": (
        "Function arguments are missing type annotations. Please add type annotations",
        "missing-arg-type-annoation",
        "Function arguments are missing type annotations. Please add type annotations",),
    "W9018": (
        "NotImplementedError was not raised in the else cause of main function. Please raise NotImplementedError "
        "exception",
        "not-implemented-error-doesnt-exist",
        "NotImplementedError was not raised in the else cause of main function. Please raise NotImplementedError "
        "exception",),
}


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1
    msgs = xsoar_msg

    def __init__(self, linter=None):
        super(XsoarChecker, self).__init__(linter)

    def visit_functiondef(self, node):
        self._type_annotations_checker(node)
        self._not_implemented_error_in_main(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _type_annotations_checker(self, node):
        try:
            if not os.getenv('PY2'):
                annotation = True
                for ann, args in zip(node.args.annotations, node.args.args):
                    if not ann and args.name != 'self':
                        annotation = False
                if not annotation and node.name not in ['main', '__init__']:
                    self.add_message("missing-arg-type-annoation", node=node)
        except Exception:
            pass

    def _not_implemented_error_in_main(self, node):
        try:
            if node.name == 'main':
                not_implemented_error_exist = False
                for child in self._inner_search_return_error(node):
                    if isinstance(child, astroid.If):
                        else_cluse = child.orelse
                        for line in else_cluse:
                            if isinstance(line, astroid.Raise) and line.exc.func.name == "NotImplementedError":
                                not_implemented_error_exist = True
                if not not_implemented_error_exist:
                    self.add_message("not-implemented-error-doesnt-exist", node=node)
        except Exception:
            pass

    def _inner_search_return_error(self, node):
        try:
            for subnode in list(node.get_children()):
                yield subnode
                for sub in self._inner_search_return_error(subnode):
                    yield sub

        except (AttributeError, TypeError):
            yield node


def register(linter):
    linter.register_checker(XsoarChecker(linter))

# You can find documentation about adding new checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker

"""
#### How to add a new check?
1. Chose the lowest support level that the checker should check.
2. Add a new checker in the `<support>_level_checker.py` file.
    1. Add a new Error/ Warning message in the message list.
    2. Add a new checker function which includes the actual logic of the check.
    3. Add your checker function under the relevant visit/leave function so which will activate it on the node.
    * For more explanation regarding pylint plugins and how to add a new checker:
      http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker
3. Add a new unit test for your checker inside the `test_pylint_plugin` folder under the relevant support level.
4. For error messages, add your new message number in the `test_build_xsoar_linter_py3_command` and
 `test_build_xsoar_linter_py2_command` of the `command_builder_test.py` file.
5. Add the check to the `xsoar_linter_integration_test.py` test suit.
"""

import os

import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# --------------------------------------------------- Messages --------------------------------------------------------

xsoar_msg = {
    "W9014": (
        "Function arguments are missing type annotations. Please add type annotations",
        "missing-arg-type-annoation",
        "Function arguments are missing type annotations. Please add type annotations",),
    "W9018": (
        "It is best practice for Integrations to raise a NotImplementedError when receiving a command which is not "
        "recognized. "
        "exception",
        "not-implemented-error-doesnt-exist",
        "It is best practice for Integrations to raise a NotImplementedError when receiving a command which is not "
        "recognized.",),
    "W9019": (
        "It is best practice to use .get when accessing the arg/params dict object rather then direct access.",
        "direct-access-args-params-dict-exist",
        "It is best practice to use .get when accessing the arg/params dict object rather then direct access.",),

}


class XsoarChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "xsoar-checker"
    priority = -1
    msgs = xsoar_msg

    def __init__(self, linter=None):
        super(XsoarChecker, self).__init__(linter)
        self.is_script = True if os.getenv('is_script') == 'True' else False
        self.common_args_params = ['args', 'dargs', 'arguments', 'd_args', 'data_args', 'params', 'PARAMS',
                                   'integration_parameters']

    # ------------------------------------- visit functions -------------------------------------------------
    '''
    `visit_<node_name>` is a function which will be activated while visiting the node_name in the ast of the
    python code.
    When adding a new check:
    1. Add a new checker function to the validations section.
    2. Add the function's activation under the relevant visit function.
    '''

    def visit_functiondef(self, node):
        self._type_annotations_checker(node)
        self._not_implemented_error_in_main(node)

    def visit_subscript(self, node):
        self._direct_access_dict_checker(node)

# ---------------------------------------------------- Checkers  ------------------------------------------------------
    '''
    Checker functions are the functions that have the logic of our check and should be activated in one or more
     visit/leave functions.
    '''

    # -------------------------------------------- FuncDef Node ---------------------------------------------

    def _type_annotations_checker(self, node):
        """
        Args: node which is a FuncDef Node.
        Check:
        - if all arguments have type annotation for Python3 env.

        Adds the relevant error message using `add_message` function if annotations are missing.
        """
        try:
            # Argument typing isn't implemented for Python2
            if not os.getenv('PY2'):
                annotation = True

                # Checks that each arg has type annotation.
                for ann, args in zip(node.args.annotations, node.args.args):
                    if not ann and args.name != 'self':
                        annotation = False

                if not annotation and node.name not in ['main', '__init__']:
                    self.add_message("missing-arg-type-annoation", node=node)

        except Exception:
            pass

    def _not_implemented_error_in_main(self, node):
        """
        Args: node which is a FuncDef Node.
        Check:
        - if inside the main function NotImplementedError is raised.

        Adds the relevant error message using `add_message` function if error is missing.
        """
        try:
            # exclude scripts as are not obligated to raise NotImplementedError in the main func.
            if not self.is_script:

                if node.name == 'main':
                    not_implemented_error_exist = False

                    # Iterate over each child node of the FuncDef main Node.
                    for child in self._inner_search(node):

                        # In case the NotImplementedError appears as part of a raise node.
                        if isinstance(child, astroid.Raise) and child.exc.func.name == "NotImplementedError":
                            not_implemented_error_exist = True

                        # In case the NotImplementedError appears inside of a If node.
                        if isinstance(child, astroid.If):
                            if_clause = child.body
                            else_clause = child.orelse
                            clauses = if_clause + else_clause

                            # Iterate over each clause of the if node and search for raise NotImplementedError.
                            for line in clauses:
                                if isinstance(line, astroid.Raise) and line.exc.func.name == "NotImplementedError":
                                    not_implemented_error_exist = True
                                    break

                        if not_implemented_error_exist:
                            break

                    if not not_implemented_error_exist:
                        self.add_message("not-implemented-error-doesnt-exist", node=node)

        except Exception:
            pass

    # -------------------------------------------- SubScript Node ---------------------------------------------

    def _direct_access_dict_checker(self, node):
        """
        Args: node which is a SubScript Node.
        Check:
        - if demisto.args()/ demisto.params statement are accessed directly .
        - if args/ params variables are accessed directly.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            # for demisto.args()[] implementation or for demisto.params()[]
            if isinstance(node.parent, astroid.Assign) and node not in node.parent.targets:

                # Checks for demisto.args()[] implementation.
                if node.value.func.expr.name == 'demisto' and node.value.func.attrname == 'args':
                    self.add_message("direct-access-args-params-dict-exist", node=node)

                # Checks for demisto.params()[] implementation.
                elif node.value.func.expr.name == 'demisto' and node.value.func.attrname == 'params':
                    self.add_message("direct-access-args-params-dict-exist", node=node)

        except Exception:
            try:
                # for args[]/params[] implementation which is not in the left (target) side of the assignment(=)
                if isinstance(node.parent, astroid.Assign) and node not in node.parent.targets:
                    if node.value.name in self.common_args_params:
                        self.add_message("direct-access-args-params-dict-exist", node=node)

            except Exception:
                pass

# ------------------------------------------------ Helper Function ----------------------------------------------------

    def _inner_search(self, node):
        """
        Args: node which is an Astroid Node.
        A generator for the children's of a given astroid node.
        """
        try:
            for subnode in list(node.get_children()):
                yield subnode

                for sub in self._inner_search(subnode):
                    yield sub

        except (AttributeError, TypeError):
            yield node


def register(linter):
    linter.register_checker(XsoarChecker(linter))

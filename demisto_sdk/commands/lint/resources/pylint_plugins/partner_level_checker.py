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

import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# --------------------------------------------------- Messages --------------------------------------------------------

partner_msg = {
    "W9010": (
        "try and except statements were not found in main function. Please add them",
        "try-except-main-doesnt-exists",
        "Ensure to not try except in the main function.",
    ),
    "W9011": (
        "return_error used too many times, should be used only once in the code, in main function. Please remove "
        "other usages.",
        "too-many-return-error",
        "return.error should be used only once in the code",
    ),
    "W9012": (
        "return_error should be used in main function. Please add it.",
        "return-error-does-not-exist-in-main",
        "return_error should be used in main function",
    ),
}


class PartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "partner-checker"
    priority = -1
    msgs = partner_msg

    def __init__(self, linter=None):
        super().__init__(linter)
        self.return_error_count = 0

    # ------------------------------------- visit functions -------------------------------------------------
    """
    `visit_<node_name>` is a function which will be activated while visiting the node_name in the ast of the
    python code.
    When adding a new check:
    1. Add a new checker function to the validations section.
    2. Add the function's activation under the relevant visit function.
    """

    def visit_call(self, node):
        self._return_error_function_count(node)

    def visit_functiondef(self, node):
        self._try_except_in_main(node)
        self._return_error_in_main_checker(node)

    # ------------------------------------- leave functions -------------------------------------------------
    """
    `leave_<node_name>` is a function which will be activated while leaving the node_name in the ast of the
    python code.
    When adding a new check:
    1. Add a new checker function to the validations section.
    2. Add the function's activation under the relevant leave function.

    * leave_module will be activated at the end of the file.
    """

    def leave_module(self, node):
        self._return_error_count_checker(node)

    # ---------------------------------------------------- Checkers  ------------------------------------------------------
    """
    Checker functions are the functions that have the logic of our check and should be activated in one or more
     visit/leave functions.
    """

    # -------------------------------------------- Call Node ---------------------------------------------

    def _return_error_function_count(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if return_error() statement exists in the current node.

        Increases the counter of return_error.
        """
        try:
            if node.func.name == "return_error":
                self.return_error_count = self.return_error_count + 1

        except AttributeError:
            pass

    # -------------------------------------------- FuncDef Node ---------------------------------------------

    def _try_except_in_main(self, node):
        """
        Args: node which is a FuncDef Node.
        Check:
        - if try and except statement doesn't exists in the current node which is the main function def.

        Adds the relevant error message using `add_message` function.
        """
        if node.name == "main":
            try_except_exists = False

            # Iterate over the children nodes of the main function node and search for Try/ TryFinally node.
            for child in node.get_children():
                if isinstance(child, astroid.TryExcept) or isinstance(
                    child, astroid.TryFinally
                ):
                    try_except_exists = True

            if not try_except_exists:
                self.add_message("try-except-main-doesnt-exists", node=node)

    def _return_error_in_main_checker(self, node):
        """
        Args: node which is a FuncDef Node.
        Check:
        - if return_error() statement exists in the current node which is the main function def.

        Adds the relevant error message using `add_message` function if return error does not exist in main func.
        """
        try:
            if node.name == "main":
                return_error_exists = False
                for child in self._inner_search_return_error(node):
                    if isinstance(child, astroid.Call):
                        try:
                            if child.func.name == "return_error":
                                return_error_exists = True

                        except AttributeError:
                            pass

                if not return_error_exists:
                    self.add_message("return-error-does-not-exist-in-main", node=node)

        except AttributeError:
            pass

    # -------------------------------------------- Module Node ---------------------------------------------

    def _return_error_count_checker(self, node):
        """
        Args: node which is a Module Node.
        Check:
        - if return_error() statement exists more then once in the python code using the counter.

        Adds the relevant error message using `add_message` function if exists more then once.
        """
        if self.return_error_count > 1:
            self.add_message("too-many-return-error", node=node)

    # ------------------------------------------------ Helper Function ----------------------------------------------------

    def _inner_search_return_error(self, node):
        """
        Args: node which is an Astroid Node.
        A generator for the children's of a given astroid node.
        """
        try:
            for subnode in list(node.get_children()):
                yield subnode

                yield from self._inner_search_return_error(subnode)

        except AttributeError:
            yield node

        except TypeError:
            yield node


def register(linter):
    linter.register_checker(PartnerChecker(linter))

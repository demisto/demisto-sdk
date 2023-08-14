# You can find documentation about adding new checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker

"""
#### How to add a new check?
1. Choose the lowest support level that the checker should check.
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


from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# -------------------------------------------- Messages for all linters ------------------------------------------------

branch_base_msg = {
    "E9013": (
        "LOG is found, Please replace all LOG usage with demisto.info or demisto.debug",
        "LOG-exists",
        "Please remove all LOG usage and exchange it with demisto.info/demisto.debug",
    )
}


class BranchCustomBaseChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "branch-base-checker"
    priority = -1
    msgs = branch_base_msg

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
        self._LOG_checker(node)

    # ---------------------------------------------------- Checkers  ----------------------------------------
    """
    Checker functions are the functions that have the logic of our check and should be activated in one or more
     visit/leave functions.
    """

    # -------------------------------------------- Call Node ---------------------------------------------
    def _LOG_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if LOG() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.name == "LOG":
                self.add_message("LOG-exists", node=node)

        except Exception:
            pass


def register(linter):
    linter.register_checker(BranchCustomBaseChecker(linter))

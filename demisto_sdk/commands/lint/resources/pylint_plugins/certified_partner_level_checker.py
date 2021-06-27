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

# -------------------------------------------- Messages ------------------------------------------------

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
    "W9016": ("Initialize of params was found outside of main function. Please use demisto.params() only inside main "
              "func",
              "init-params-outside-main",
              "Initialize of params was found outside of main function. Please initialize params only inside main func",),
    "W9017": ("Initialize of args was found outside of main function. Please use demisto.args() only inside main func",
              "init-args-outside-main",
              "Initialize of args was found outside of main function. Please use demisto.args() only inside main func",),

}


class CertifiedPartnerChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "certified-partner-checker"
    priority = -1
    msgs = cert_partner_msg

    def __init__(self, linter=None):
        super(CertifiedPartnerChecker, self).__init__(linter)
        self.list_of_function_names = set()

    # ------------------------------------- visit functions -------------------------------------------------
    '''
    `visit_<node_name>` is a function which will be activated while visiting the node_name in the ast of the
    python code.
    When adding a new check:
    1. Add a new checker function to the validations section.
    2. Add the function's activation under the relevant visit function.
    '''

    def visit_call(self, node):
        self._sys_exit_checker(node)
        self._demisto_log_checker(node)
        self._return_outputs_checker(node)
        self._demisto_results_checker(node)
        self._init_params_checker(node)
        self._init_args_checker(node)

    def visit_functiondef(self, node):
        self.list_of_function_names.add(node.name)

    # ------------------------------------- leave functions -------------------------------------------------
    '''
    `leave_<node_name>` is a function which will be activated while leaving the node_name in the ast of the
    python code.
    When adding a new check:
    1. Add a new checker function to the validations section.
    2. Add the function's activation under the relevant leave function.

    * leave_module will be activated at the end of the file.
    '''

    def leave_module(self, node):
        self._main_function(node)

# ---------------------------------------------------- Checkers  ------------------------------------------------------
    '''
    Checker functions are the functions that have the logic of our check and should be activated in one or more
     visit/leave functions.
    '''

    # -------------------------------------------- Call Node ---------------------------------------------

    def _sys_exit_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if sys.exit() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.attrname == 'exit' and node.func.expr.name == 'sys' and node.args and node.args[0].value != 0:
                self.add_message("sys-exit-exists", node=node)

        except Exception:
            pass

    def _demisto_log_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if demisto.log() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.attrname == 'log' and node.func.expr.name == 'demisto':
                self.add_message("demisto-log-exists", node=node)

        except Exception:
            pass

    def _return_outputs_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if return_outputs() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.name == 'return_outputs':
                self.add_message("return-outputs-exists", node=node)

        except Exception:
            pass

    def _demisto_results_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if demisto.results() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.attrname == 'results' and node.func.expr.name == 'demisto':
                self.add_message("demisto-results-exists", node=node)

        except Exception:
            pass

    def _init_params_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if demisto.params() statement exists and if its parent node is main().

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.attrname == 'params' and node.func.expr.name == 'demisto':
                check_param = True
                parent = node.parent

                # check if main function is one of the parent nodes of the current node that contains demisto.params()
                while check_param and parent:
                    if isinstance(parent, astroid.FunctionDef) and parent.name == 'main':
                        check_param = False
                    parent = parent.parent

                if check_param:
                    self.add_message("init-params-outside-main", node=node)

        except AttributeError:
            pass

    def _init_args_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if demisto.args() statement exists and if its parent node is main().

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.attrname == 'args' and node.func.expr.name == 'demisto':
                check_param = True
                parent = node.parent

                # check if main function is one of the parent nodes of the current node that contains demisto.params()
                while check_param and parent:
                    if isinstance(parent, astroid.FunctionDef) and parent.name == 'main':
                        check_param = False
                    parent = parent.parent

                if check_param:
                    self.add_message("init-args-outside-main", node=node)

        except AttributeError:
            pass

    # -------------------------------------------- Module Node ---------------------------------------------

    def _main_function(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if main() function exists in the code.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        if 'main' not in self.list_of_function_names:
            self.add_message("main-func-doesnt-exist", node=node)


def register(linter):
    linter.register_checker(CertifiedPartnerChecker(linter))

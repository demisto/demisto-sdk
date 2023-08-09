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

import os

import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# -------------------------------------------- Messages for all linters ------------------------------------------------

base_msg = {
    "E9002": (
        "Print is found, Please remove all prints from the code.",
        "print-exists",
        "Please remove all prints from the code.",
    ),
    "E9003": (
        "Sleep is found, Please remove all sleep statements from the code.",
        "sleep-exists",
        "Please remove all sleep statements from the code.",
    ),
    "E9004": (
        "exit is found, Please remove all exit() statements from the code.",
        "exit-exists",
        "Please remove all exit() statements from the code.",
    ),
    "E9005": (
        "quit is found, Please remove all quit() statements from the code.",
        "quit-exists",
        "Please remove all quit statements from the code.",
    ),
    "E9006": (
        "Invalid CommonServerPython import was found. Please change the import to: "
        "from CommonServerPython import *",
        "invalid-import-common-server-python",
        "Please change the import to: from CommonServerPython import *",
    ),
    "E9007": (
        "Invalid usage of indicators key in CommandResults was found, Please use indicator key instead.",
        "commandresults-indicators-exists",
        "Invalid usage of indicators key in CommandResults was found, Please use indicator key instead.",
    ),
    "E9010": (
        "Some commands from yml file are not implemented in the python file, Please make sure that every "
        "command is implemented in your code. The commands that are not implemented are %s",
        "unimplemented-commands-exist",
        "Some commands from yml file are not implemented in the python file, Please make sure that every "
        "command is implemented in your code.",
    ),
    "E9011": (
        "test-module command is not implemented in the python file, it is essential for every"
        " integration. Please add it to your code. For more information see: "
        "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
        "unimplemented-test-module",
        "test-module command is not implemented in the python file, it is essential for every"
        " integration. Please add it to your code. For more information see: "
        "https://xsoar.pan.dev/docs/integrations/code-conventions#test-module",
    ),
    "E9012": (
        "Demisto.log is found, Please replace all demisto.log usage with demisto.info or demisto.debug",
        "demisto-log-exists",
        "Please remove all demisto.log usage and exchange it with demisto.info/demisto.debug",
    ),
    "W9013": (
        "Hardcoded http URL was found in the code, using https (when possible) is recommended.",
        "http-usage",
        "Please use the https method if possible",
    ),
}

TEST_MODULE = "test-module"
BUILD_IN_COMMANDS = [
    "getIncidents",
    "DeleteContext",
    "isWhitelisted",
    "excludeIndicators",
    "deleteIndicators",
    "extractIndicators",
]


class CustomBaseChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "base-checker"
    priority = -1
    msgs = base_msg

    def __init__(self, linter=None):
        super().__init__(linter)
        self.commands = (
            os.getenv("commands", "").split(",") if os.getenv("commands") else []
        )
        self.is_script = True if os.getenv("is_script") == "True" else False
        # we treat scripts as they already implement the test-module
        self.test_module_implemented = False if not self.is_script else True

    # ------------------------------------- visit functions -------------------------------------------------
    """
    `visit_<node_name>` is a function which will be activated while visiting the node_name in the ast of the
    python code.
    When adding a new check:
    1. Add a new checker function to the validations section.
    2. Add the function's activation under the relevant visit function.
    """

    def visit_call(self, node):
        self._print_checker(node)
        self._sleep_checker(node)
        self._quit_checker(node)
        self._exit_checker(node)
        self._commandresults_indicator_check(node)
        self._demisto_log_checker(node)

    def visit_const(self, node):
        self._http_checker(node)

    def visit_importfrom(self, node):
        self._common_server_import(node)
        self._api_module_import_checker(node)

    # Print statement for Python2 only.
    def visit_print(self, node):
        self.add_message("print-exists", node=node)

    def visit_dict(self, node):
        self._commands_in_dict_keys_checker(node)

    def visit_if(self, node):
        self._commands_in_if_statment_checker(node)

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
        self._all_commands_implemented(node)
        self._test_module_implemented(node)

    # ---------------------------------------------------- Checkers  ------------------------------------------------------
    """
    Checker functions are the functions that have the logic of our check and should be activated in one or more
     visit/leave functions.
    """

    # -------------------------------------------- Call Node ---------------------------------------------

    def _print_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if print() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.name == "print":
                self.add_message("print-exists", node=node)

        except Exception:
            pass

    def _sleep_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if time.sleep() statement exists in the current node and the arguments value is larger then 10.
        - check if sleep() statement exists in the current node and the arguments value is larger then 10.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        # checker only relevant for regular runs, long running can contain sleep statements.
        if not os.getenv("LONGRUNNING"):
            try:
                # check if time.sleep() statement exists in the current node.
                if (
                    node.func.attrname == "sleep"
                    and node.func.expr.name == "time"
                    and node
                    and int(node.args[0].value) > 10
                ):
                    self.add_message("sleep-exists", node=node)

            except Exception as exp:
                if str(exp) == "'Name' object has no attribute 'value'":
                    self.add_message("sleep-exists", node=node)
                else:
                    # check if sleep() statement exists in the current node.
                    try:
                        if node.func.name == "sleep" and int(node.args[0].value) > 10:
                            self.add_message("sleep-exists", node=node)

                    except AttributeError as e:
                        if str(e) == "'Name' object has no attribute 'value'":
                            self.add_message("sleep-exists", node=node)
                        else:
                            pass

    def _exit_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if exit() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.name == "exit":
                self.add_message("exit-exists", node=node)

        except Exception:
            pass

    def _quit_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if quit() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.name == "quit":
                self.add_message("quit-exists", node=node)
        except Exception:
            pass

    def _commandresults_indicator_check(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if CommandResults() statement exists in the current node and has an argument named indicators.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.name == "CommandResults":
                for keyword in node.keywords:
                    if keyword.arg == "indicators":
                        self.add_message("commandresults-indicators-exists", node=node)

        except Exception:
            pass

    def _http_checker(self, node):
        """
        Args: node which is a Const Node.
        Check:
        - if a hard codded http url exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """

        if isinstance(node.value, str) and node.value.startswith("http:"):
            self.add_message("http-usage", node=node)

    def _demisto_log_checker(self, node):
        """
        Args: node which is a Call Node.
        Check:
        - if demisto.log() statement exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.func.attrname == "log" and node.func.expr.name == "demisto":
                self.add_message("demisto-log-exists", node=node)

        except Exception:
            pass

    # -------------------------------------------- Import From Node ---------------------------------------------

    def _common_server_import(self, node):
        """
        Args: node which is a importFrom Node.
        Check:
        - if an import of CommonServerPython with * exists in the current node.

        Adds the relevant error message using `add_message` function if one of the above exists.
        """
        try:
            if node.modname == "CommonServerPython" and not node.names[0][0] == "*":
                self.add_message("invalid-import-common-server-python", node=node)
        except Exception:
            pass

    def _api_module_import_checker(self, node):
        """
        Args: node which is a importFrom Node.
        Check:
        - if an import of ApiModule exists in the current node.

        If an import exists we will set the commands as implemented because the implementation exist in the Api Module
        code.
        """
        try:
            if "ApiModule" in node.modname:
                self.commands = []
                self.test_module_implemented = True

        except Exception:
            pass

    # -------------------------------------------- Dict Node ---------------------------------------------

    def _commands_in_dict_keys_checker(self, node):
        """
        Args: node which is a Dict Node.

        Loop every key in the dict and remove from commands list the implemented command.
        After this function `_all_commands_implemented` will run and check if all commands were implemented.

        """
        # Astroid have different functionality for the Dict Node of Python2 and Python3, thus the logic is divided.

        # for py2
        if os.getenv("PY2"):
            try:
                for item in node.items:
                    # infer the value of each dict key (the command name)
                    commands = self._infer_name(item[0])

                    for command in commands:
                        # check if command name appear as a key of the dict

                        if command in self.commands:
                            self.commands.remove(command)

                        # check if test-module command implemented.
                        if not self.test_module_implemented and command == TEST_MODULE:
                            self.test_module_implemented = True

            except Exception:
                pass

        # for py3
        else:
            try:
                for sub_node in node.itered():
                    # infer the value of each dict key (the command name)
                    commands = self._infer_name(sub_node)

                    for command in commands:
                        # check if command name appear as a key of the dict
                        if command in self.commands:
                            self.commands.remove(command)

                        # check if test-module command implemented.
                        if not self.test_module_implemented and command == TEST_MODULE:
                            self.test_module_implemented = True

            except Exception:
                pass

    # -------------------------------------------- If Node ---------------------------------------------

    def _commands_in_if_statment_checker(self, node):
        """
        Args: node which is a If Node.
        Check all possible appearances of implementations of commands in an If statement:
        - if command exist in a regular if statement e.g. if 'command' == command
        - if command exist in a regular if with conditions e.g. command == 'command1' or command == 'commands2
        - if command exist in a elif clause of an if.
        - if command exist in a list / dict of commands e.g. ['command1','command2']  or {'command1','command2'}
        - if command exist in a tuple of commands e.g. ('command1','command2')

        Adds the relevant error message using `add_message` function if one of the above exists.
        """

        def _check_if(comp_with):
            """
            Internal function that inferences the value of the comp_with argument.
            If the inferred value is a command which is in the commands list, removes it , as we found an implementation
            Returns:

            """
            # for regular if 'command' == command with inference mechanize
            commands = self._infer_name(comp_with)

            for command in commands:
                if command in self.commands:
                    self.commands.remove(command)

                if not self.test_module_implemented and command == TEST_MODULE:
                    self.test_module_implemented = True

            # for if command in ['command1','command2'] or for if command in {'command1','command2'}
            if isinstance(comp_with, astroid.List) or isinstance(
                comp_with, astroid.Set
            ):
                for var_lst in comp_with.itered():
                    commands = self._infer_name(var_lst)

                    for command in commands:
                        if command in self.commands:
                            self.commands.remove(command)
                        if not self.test_module_implemented and command == TEST_MODULE:

                            self.test_module_implemented = True

            # for if command in ('command1','command2')
            elif isinstance(comp_with, astroid.Tuple):
                for var_lst in comp_with.elts:
                    commands = self._infer_name(var_lst)

                    for command in commands:
                        if command in self.commands:
                            self.commands.remove(command)

                        if not self.test_module_implemented and command == TEST_MODULE:
                            self.test_module_implemented = True

        try:
            # for if command == 'command1' or command == 'commands2'
            if isinstance(node.test, astroid.BoolOp):
                for value in node.test.values:
                    _check_if(value.ops[0][1])

            # for regular if
            _check_if(node.test.ops[0][1])

            # for elif clause
            for elif_clause in node.orelse:
                _check_if(elif_clause.test.ops[0][1])

        except Exception:
            pass

    # --------------------------------------- Module Node ---------------------------------------------------

    def _all_commands_implemented(self, node):
        """
        Args: node which is a Module Node.
        Checks that when leaving module all implementations of commands ( in if statements or dict statements )
        were found.

        Adds the relevant error message using `add_message` function if there were commands which are not implemented.
        """
        if self.commands:
            self.add_message(
                "unimplemented-commands-exist", args=str(self.commands), node=node
            )

    def _test_module_implemented(self, node):
        """
        Args: node which is a Module Node.
        Checks that when leaving module test-module implementation was found.

        Adds the relevant error message using `add_message` function if the implementation was not found.
        """
        if not self.test_module_implemented:
            self.add_message("unimplemented-test-module", node=node)

    #  ---------------------------------------------- Helper Function ----------------------------------------------------

    def _infer_name(self, comp_with):
        """
        Args: comp_with the value on which we are trying to infer its value.

        The function can get as an input the following cases:
        - A case of a formatted string input with a variable in it e.g. f'{variable}-test1' .
        - A case of a formatted string input with a constant in it e.g. f'test1'.
        - A case of a name input.
        - A case of a name constant e.g. '10'.

        Returns: a list of inferred values of comp_with.
        """

        def _infer_single_var(var):
            var_infered = []
            try:
                for inference in var.infer():
                    var_infered.append(inference.value)

            except astroid.InferenceError:
                pass

            return var_infered

        infered = []

        # In case of a formatted string input
        if isinstance(comp_with, astroid.JoinedStr):
            for value in comp_with.values:

                # In a case of formatted string with a variable
                if isinstance(value, astroid.FormattedValue):
                    infered.extend(_infer_single_var(value.value))

                # In a case of formatted string with a constant var.
                elif isinstance(value, astroid.Const):
                    infered.append(value.value)

            infered = ["".join(infered)]

        # In case of a name input
        elif isinstance(comp_with, astroid.Name):
            infered = _infer_single_var(comp_with)

        # In case of a constant input
        elif isinstance(comp_with, astroid.Const):
            infered = [comp_with.value]

        return infered


def register(linter):
    linter.register_checker(CustomBaseChecker(linter))

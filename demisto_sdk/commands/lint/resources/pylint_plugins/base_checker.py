import os

import astroid
from pylint.checkers import BaseChecker
from pylint.interfaces import IAstroidChecker

# You can find documentation about adding new checker here:
# http://pylint.pycqa.org/en/latest/how_tos/custom_checkers.html#write-a-checker

base_msg = {
    "E9002": ("Print is found, Please remove all prints from the code.", "print-exists",
              "Please remove all prints from the code.",),
    "E9003": ("Sleep is found, Please remove all sleep statements from the code.", "sleep-exists",
              "Please remove all sleep statements from the code.",),
    "E9004": ("exit is found, Please remove all exit() statements from the code.", "exit-exists",
              "Please remove all exit() statements from the code.",),
    "E9005": ("quit is found, Please remove all quit() statements from the code.", "quit-exists",
              "Please remove all quit statements from the code.",),
    "E9006": ("Invalid CommonServerPython import was found. Please change the import to: "
              "from CommonServerPython import *", "invalid-import-common-server-python",
              "Please change the import to: from CommonServerPython import *"),
    "E9008": ("Some args from yml file are not implemented in the python file, Please make sure that every arg is "
              "implemented in your code. The arguments that are not implemented are %s",
              "unimplemented-args-exist",
              "Some args from yml file are not implemented in the python file, Please make sure that every arg is "
              "implemented in your code"),
    "E9009": ("Some parameters from yml file are not implemented in the python file, Please make sure that every "
              "param is implemented in your code. The params that are not implemented are %s",
              "unimplemented-params-exist",
              "Some parameters from yml file are not implemented in the python file, Please make sure that every "
              "param is implemented in your code.")
}


# -------------------------------------------- Messages for all linters ------------------------------------------------


class CustomBaseChecker(BaseChecker):
    __implements__ = IAstroidChecker
    name = "base-checker"
    priority = -1
    msgs = base_msg

    def __init__(self, linter=None):
        super(CustomBaseChecker, self).__init__(linter)
        self.args_list = os.getenv('args').split(',') if os.getenv('args') else []
        self.param_list = os.getenv('params').split(',') if os.getenv('params') else []
        self.feed_params = os.getenv('feed_params').split(',') if os.getenv('feed_params') else []

    def visit_call(self, node):
        self._print_checker(node)
        self._sleep_checker(node)
        self._quit_checker(node)
        self._exit_checker(node)
        self._arg_implemented_get_check(node)
        self._params_implemented_get_check(node)
        self._handle_proxy_exist_checker(node)

    def visit_importfrom(self, node):
        self._common_server_import(node)
        self._api_module_import_checker(node)

    # Print statment for Python2 only.
    def visit_print(self, node):
        self.add_message("print-exists", node=node)

    def visit_subscript(self, node):
        self._arg_implemented_index_check(node)
        self._params_implemented_index_check(node)

    def leave_module(self, node):
        self._all_args_implemented(node)
        self._all_params_implemented(node)

    # -------------------------------------------- Validations--------------------------------------------------

    def _print_checker(self, node):
        try:
            if node.func.name == 'print':
                self.add_message("print-exists", node=node)
        except Exception:
            pass

    def _sleep_checker(self, node):
        if not os.getenv('LONGRUNNING'):
            try:
                if node.func.attrname == 'sleep' and node.func.expr.name == 'time' and node and int(
                        node.args[0].value) > 10:
                    self.add_message("sleep-exists", node=node)
            except Exception as exp:
                if str(exp) == "'Name' object has no attribute 'value'":
                    self.add_message("sleep-exists", node=node)
                else:
                    try:
                        if node.func.name == 'sleep' and int(node.args[0].value) > 10:
                            self.add_message("sleep-exists", node=node)
                    except AttributeError as e:
                        if str(e) == "'Name' object has no attribute 'value'":
                            self.add_message("sleep-exists", node=node)
                        else:
                            pass

    def _exit_checker(self, node):
        try:
            if node.func.name == 'exit':
                self.add_message("exit-exists", node=node)
        except Exception:
            pass

    def _quit_checker(self, node):
        try:
            if node.func.name == 'quit':
                self.add_message("quit-exists", node=node)
        except Exception:
            pass

    def _common_server_import(self, node):
        try:
            if node.modname == 'CommonServerPython' and not node.names[0][0] == '*':
                self.add_message("invalid-import-common-server-python", node=node)
        except Exception:
            pass

    def _handle_proxy_exist_checker(self, node):
        try:
            if node.func.name == "handle_proxy" and "proxy" in self.param_list:
                self.param_list.remove("proxy")
        except Exception:
            pass

    def _api_module_import_checker(self, node):
        try:
            # for feeds which use api module -> the feed required params are implemented in the api module code.
            # as a result we will remove them from param list.
            if 'ApiModule' in node.modname:
                for param in self.feed_params:
                    if param in self.param_list:
                        self.param_list.remove(param)
        except Exception:
            pass

    def _arg_implemented_get_check(self, node):
        try:
            if node.func.attrname == 'get' or node.func.attrname == 'getArg':
                for get_arg in node.args:
                    if get_arg.value in self.args_list:
                        self.args_list.remove(get_arg.value)

        except Exception:
            pass

    def _arg_implemented_index_check(self, node):
        try:
            # for demisto.args()['arg'] implementation
            if node.value.func.expr.name == 'demisto' and node.value.func.attrname == 'args' and node.slice.value.value in self.args_list:
                self.args_list.remove(node.slice.value.value)
        except Exception:
            try:
                # for args['arg'] implementation
                if node.value.name == 'args' and node.slice.value.value in self.args_list:
                    self.args_list.remove(node.slice.value.value)
            except Exception:
                pass

    def _params_implemented_get_check(self, node):
        try:
            if node.func.attrname == 'get' or node.func.attrname == 'getParam':
                for get_param in node.args:
                    if get_param.value in self.param_list:
                        self.param_list.remove(get_param.value)
                    # for credentials case where the argument is credential but usually implement with another get
                    elif node.func.expr.func.attrname == 'get':
                        for get_param in node.func.expr.args:
                            if get_param.value in self.param_list:
                                self.param_list.remove(get_param.value)
        except Exception:
            pass

    def _params_implemented_index_check(self, node):
        try:
            # for demisto.params()['param'] implementation
            if isinstance(node.value,
                          astroid.Call) and node.value.func.expr.name == 'demisto' and node.value.func.attrname == 'params' and \
                    node.slice.value.value in self.param_list:
                self.param_list.remove(node.slice.value.value)

            # for params['param'] implementation
            elif isinstance(node.value,
                            astroid.Name) and node.value.name == 'params' and node.slice.value.value in self.param_list:
                self.param_list.remove(node.slice.value.value)

            # for double index ['cred']['id']
            elif isinstance(node.value, astroid.Subscript):
                # for demisto.params()['cred']['identifier']
                if isinstance(node.value.value,
                              astroid.Call) and node.value.value.func.expr.name == 'demisto' and node.value.value.func.attrname == 'params' and \
                        node.value.slice.value.value in self.param_list:
                    self.param_list.remove(node.value.slice.value.value)
                # for params['cred']['identifier']
                elif isinstance(node.value.value,
                                astroid.Name) and node.value.value.name == 'params' and node.value.slice.value.value in self.param_list:
                    self.param_list.remove(node.value.slice.value.value)

        except Exception:
            pass

    def _all_args_implemented(self, node):
        if self.args_list:
            self.add_message("unimplemented-args-exist",
                             args=str(self.args_list), node=node)

    def _all_params_implemented(self, node):
        if self.param_list:
            self.add_message("unimplemented-params-exist",
                             args=str(self.param_list), node=node)


def register(linter):
    linter.register_checker(CustomBaseChecker(linter))

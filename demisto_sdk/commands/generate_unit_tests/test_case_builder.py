import ast as ast_mod
from pathlib import Path
from typing import Dict, List, Union

from ordered_set import OrderedSet

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.generate_unit_tests.common import (
    ast_name,
    extract_outputs_from_command_run,
)


class ArgsBuilder:
    def __init__(
        self,
        command_name: str,
        directory_path: str,
        args_list: List[str] = [],
        commands_to_generate: Dict[str, List[str]] = {},
    ):
        self.args_list = args_list
        self.command_name = command_name
        self.directory_path = directory_path
        self.args = []
        self.global_arg = []
        self.global_arg_name = None
        self.decorators = []
        self.commands_to_generate = commands_to_generate
        self.input_args = commands_to_generate.get(self.command_name)
        self.build_args()

    # ================= Argument builders =====================

    def build_args(self):
        """
        Args: args_keys: names of the arguments provided for the command
              input: dictionary of mocked inputs from the user
        Returns: ast node of type assign 'args = {test:'mock'}'
        """
        if self.input_args:
            is_parametrize = (
                True
                if len(self.commands_to_generate.get(self.command_name)) > 1
                else False
            )
            if is_parametrize:
                logger.debug("Creating global argument object for parametrize.")
                self.build_global_args()
                self.build_decorator()
            else:
                logger.debug("Creating local argument object for parametrize.")
                self.build_local_args()

    def get_keys_values(self, input_arg: dict):
        """
        parsing input arguments into an ast dictionary.
        """
        keys = []
        values = []
        for arg in self.args_list:
            value = input_arg.get(arg)
            if value is not None:
                value.replace('"', "")
            keys.append(ast_mod.Constant(value=arg))
            values.append(ast_mod.Constant(value=value))
        return keys, values

    def build_local_args(self):
        """
        build a local var named args that will be given as input to the command.
        """
        keys, values = self.get_keys_values(self.input_args[0])
        self.args.append(
            ast_mod.Assign(
                targets=[ast_name("args", ctx=ast_mod.Store())],
                value=ast_mod.Dict(keys=keys, values=values),
            )
        )

    def build_global_args(self):
        """
        builds a global var named after the command name, it will hold all arguments given.
        """
        self.global_arg_name = f"{self.command_name.upper()}_ARGS"
        global_args = []
        for inputs in self.input_args:
            keys, values = self.get_keys_values(inputs)
            global_args.append(ast_mod.Dict(keys=keys, values=values))
        self.global_arg.append(
            ast_mod.Assign(
                targets=[ast_name(self.global_arg_name, ast_mod.Store())],
                value=ast_mod.List(elts=global_args, ctx=ast_mod.Store()),
            )
        )

    # ================= Decorator builder =====================

    def build_decorator(self):
        """
        builds decorator of parametrize.
        """
        call = ast_mod.Call(
            func=ast_name("pytest.mark.parametrize"),
            args=[ast_mod.Constant("args"), ast_name(self.global_arg_name)],
            keywords=[],
        )
        self.decorators.append(call)


class TestCase:
    def __init__(
        self,
        func: ast_mod.FunctionDef,
        directory_path: Path,
        client_ast: ast_mod.ClassDef,
        example_dict: dict,
        id: int = 0,
        module: ast_mod.Module = None,
    ):
        self.asserts = []
        self.func = func
        self.id = id
        self.module = module
        self.mocks = []
        self.inputs = []
        self.command_call = None
        self.comment = "\n\tWhen:\n\tGiven:\n\tThen:\n\t"
        self.directory_path = directory_path
        self.client_func_call = []
        self.args = []
        self.args_list = []
        self.client_ast = client_ast
        self.client_name = None
        self.decorators = []
        self.global_arg = None
        self.examples_dict = example_dict
        self.get_client_name()
        self.instance_dict_parser()

    def to_ast(self):
        """
        Converting test_case object to ast.
        """
        body = [ast_mod.Expr(value=ast_mod.Constant(value=self.comment))]
        body.extend(self.inputs)
        body.extend(self.mocks)
        body.append(self.command_call)
        body.extend(self.asserts)
        request_mocker = ast_name("requests_mock")

        args = [self.client_name, request_mocker]
        if self.global_arg:
            args.append(ast_name("args"))

        test_func = ast_mod.FunctionDef(
            name=f"test_{self.func.name}",
            args=ast_mod.arguments(
                posonlyargs=[],
                args=args,
                vararg=None,
                kwonlyargs=[],
                kw_defaults=[],
                kwarg=None,
                defaults=[],
            ),
            body=body,
            decorator_list=self.decorators,
            returns=None,
        )
        return test_func

    # ================= Mocks builders =====================

    def request_mock_ast_builder(self):
        """
        Builds ast nodes of requests mock.
        """
        for call in self.client_func_call:
            self.mocks.append(
                self.load_mock_from_json_ast_builder(f"mock_response_{call}", call)
            )
            self.mocks.append(
                self.load_mock_from_json_ast_builder(
                    "mock_results", str(self.func.name)
                )
            )

            suffix, method = self.get_call_params_from_http_request(call)
            url = f"SERVER_URL + '{suffix}'" if suffix is not None else "SERVER_URL"

            attr = ast_mod.Attribute(
                value=ast_name("requests_mock"), attr=ast_name(method.lower())
            )
            ret_val = ast_mod.keyword(
                arg=ast_name("json"), value=ast_name(f"mock_response_{call}")
            )
            mock_call = ast_mod.Call(
                func=attr, args=[ast_name(url)], keywords=[ret_val]
            )
            self.mocks.append(ast_mod.Expr(value=mock_call))

    def load_mock_from_json_ast_builder(self, name: str, call: str):
        """
        Args: name: name of the object to store the json.
              call: name of the call, used to decide which file to choose from outputs directory.
        Return: Assign ast node of assignment of the mocked object.
        """
        return ast_mod.Assign(
            targets=[ast_name(name, ctx=ast_mod.Store())],
            value=ast_mod.Call(
                func=ast_name("util_load_json"),
                args=[
                    ast_mod.Constant(
                        value="./" + str(Path("test_data", "outputs", f"{call}.json"))
                    )
                ],
                keywords=[],
            ),
        )

    def build_json_file_mocked_command_results(self):
        """
        Creates an output file with command line example.
        """
        prefix = self.get_context_prefix()

        if prefix is not None:
            self.examples_dict.update(
                {
                    "outputs": extract_outputs_from_command_run(
                        self.examples_dict.get("outputs"), prefix
                    )
                }
            )
            logger.debug(
                f"Creating mock command results file for {str(self.func.name)}"
            )
            Path(
                self.directory_path, "outputs", f"{str(self.func.name)}.json"
            ).write_text(json.dumps(self.examples_dict))

    def get_context_prefix(self):
        """
        Retrieves context prefix from CommandResults object
        """
        returned_value = self.get_return_values()
        if returned_value:
            keywords = returned_value.keywords
            for keyword in keywords:
                if keyword.arg == "outputs_prefix":
                    return keyword.value.value
        return None

    def get_call_params_from_http_request(self, def_name: str):
        """
        Args: def_name: name of the client function that was called.
        Return: url suffix of the API request, call method (post/get)
        """
        method = "POST"
        suffix = None
        for block in self.client_ast.body:
            if isinstance(block, ast_mod.FunctionDef) and block.name == def_name:
                for node in block.body:
                    if (
                        hasattr(node, "value")
                        and hasattr(node.value, "func")
                        and str(node.value.func) == "self._http_request"
                    ):
                        for key in node.value.keywords:
                            if hasattr(key, "arg") and key.arg == "method":
                                method = str(key.value).strip("'")
                            if hasattr(key, "arg") and key.arg == "url_suffix":
                                suffix = str(key.value).strip("'")
                    else:
                        continue
        return suffix, method

    # ================= Assertions builders =====================

    def create_command_results_assertions(self):
        """
        Args: keywords: all the params passed to CommandResults object when created.
        Return: assertion for each of the CommandResults arg.
        """
        returned_value = self.get_return_values()
        if returned_value:
            keywords = returned_value.keywords
            for keyword in keywords:
                self.asserts.append(
                    TestCase.create_command_results_assertion(
                        keyword.arg, keyword.value
                    )
                )
        else:
            logger.warning(
                "No return values were detected, thus no assertions being generated."
            )

    @staticmethod
    def assertions_builder(call: ast_mod.Attribute, ops: list, comperators: list):
        """
        Args: call: rhs of the assertions, item to check
                ops: operation to check
                comperators: values to check in the lhs
        Return: assert ast node
        """
        return ast_mod.Assert(
            test=ast_mod.Compare(left=call, ops=ops, comparators=comperators), msg=None
        )

    @staticmethod
    def get_links(value: ast_mod.Name):
        """
        returns the name of the request whom response is stored in raw_response
        """
        try:
            return value.links.func.attr
        except AttributeError:
            return None

    @staticmethod
    def create_command_results_assertion(
        arg: str, value: Union[ast_mod.Name, ast_mod.Constant]
    ):
        """
        Inputs: arg: CommandResults argument
                value: CommandResults argument value
        Returns: Single assertion as part of command results assertions
        """
        comperator = None
        call = ast_mod.Attribute(value=ast_name("results"), attr=arg)
        ops = [ast_mod.Eq()]
        if hasattr(value, "value"):
            # if so it is of type ast.Constant
            comperator = ast_mod.Constant(value=value.value)
        elif arg == "raw_response":
            link = TestCase.get_links(value)
            if link:
                comperator = ast_name(f"mock_response_{link}")
        elif arg == "outputs" or arg == "readable_output":
            get_call = ast_mod.Call(
                func=ast_name("get"), args=[ast_mod.Constant(arg)], keywords=[]
            )
            comperator = ast_mod.Attribute(
                value=ast_name("mock_results"), attr=get_call, ctx=ast_mod.Load()
            )
        return (
            TestCase.assertions_builder(call, ops, [comperator]) if comperator else None
        )

    # ================= General functions =====================

    def instance_dict_parser(self):
        """
        Args: instance_dict: dictionary of the instances built in tree from the parser
                client_name: name of the client object
        Returns: args: list of arguments given as inputs to the function
                 client_call: name of client function to mock
                 command_result: CommandResults object returned from the command
        """
        args_set = OrderedSet()
        for instance in self.func.instance_dict:
            try:
                func = str(instance.func)
                if func == "args.get":
                    args_set.add(instance.args[0].value)
                elif self.client_name is not None and func.startswith(self.client_name):
                    self.client_func_call.append(instance.func.attr)
            except AttributeError:
                pass
        self.args_list = list(args_set)

    def get_client_name(self):
        """
        Args: func: ast node of the relevant function.
               client_class_name: name of the client class.
        Return: the name of the local client instance.
        """
        if hasattr(self.func.args, "args"):
            for arg in self.func.args.args:
                if (
                    hasattr(arg, "annotation")
                    and str(arg.annotation) == self.client_ast.name
                ):
                    self.client_name = arg.arg
                    logger.debug(f"Clinet name is {arg.arg}.")

    def get_return_values(self):
        """
        Args: function ast node
        Returns: array of ast nodes of returned values
        """
        for node in self.func.return_nodes:
            if (
                hasattr(node, "value")
                and hasattr(node.value, "func")
                and str(node.value.func) == "CommandResults"
            ):
                return node.value
        if (
            hasattr(self.func.returns, "id")
            and str(self.func.returns) == "CommandResults"
        ):
            if hasattr(self.func, "locals"):
                for local_var in self.func.locals:
                    var = self.func.locals.get(local_var)
                    if hasattr(var, "func") and str(var.func) == "CommandResults":
                        return var
        return None

    def call_command_ast_builder(self):
        """
        Input: command_name: name of the command being called
        Returns: ast node of assignment command results to var.
        """
        call_keywords = [ast_mod.keyword(arg="client", value=ast_name("client"))]
        if len(self.args_list) > 0:
            call_keywords.append(ast_mod.keyword(arg="args", value=ast_name("args")))

        self.command_call = ast_mod.Assign(
            targets=[ast_name("results", ctx=ast_mod.Store())],
            value=ast_mod.Call(
                func=ast_name(self.func.name), args=[], keywords=call_keywords
            ),
        )

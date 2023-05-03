import logging
import os
import re
from distutils.util import strtobool
from pathlib import Path
from typing import Dict, List, Optional, Union

import autopep8

import demisto_sdk.commands.common.tools as tools
from demisto_sdk.commands.common.constants import ParameterType
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.generate_integration.base_code import (
    BASE_ARGUMENT,
    BASE_BASIC_AUTH,
    BASE_BEARER_TOKEN,
    BASE_CLIENT,
    BASE_CLIENT_API_KEY,
    BASE_CODE_TEMPLATE,
    BASE_CREDENTIALS,
    BASE_FUNCTION,
    BASE_HEADER,
    BASE_HEADER_API_KEY,
    BASE_HEADER_FORMATTED,
    BASE_LIST_FUNCTIONS,
    BASE_PARAMS,
    BASE_REQUEST_FUNCTION,
)
from demisto_sdk.commands.generate_integration.XSOARIntegration import XSOARIntegration

json = JSON_Handler()
yaml = YAML_Handler(width=50000)
logger = logging.getLogger("demisto-sdk")

ILLEGAL_CODE_NAMES = ["type", "from", "id", "filter", "list"]
NAME_FIX = "_"
ARGUMENT_TYPES = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "file": "str",
    "int": "int",
    "str": "str",
    "bool": "bool",
    None: None,
}


def json_body_to_code(request_json_body):
    s = json.dumps(request_json_body, sort_keys=True)
    pattern = re.compile(r"\"\{[a-zA-Z0-9_]+\}\"")
    for leaf in re.findall(pattern, s):
        s = s.replace(leaf, leaf.replace('"{', "").replace('}"', "").lower(), 1)

    return f"data={s}"


class IntegrationGeneratorOutput:
    def __init__(self, name, description, type_):
        self.name = name
        self.description = description
        self.type_ = type_


class IntegrationGeneratorArg:
    def __init__(
        self,
        name: str,
        description: Optional[str],
        type_: Optional[str] = None,
        in_: Optional[str] = None,
        default_value="",
        predefined_values: list = [],
        is_array: bool = False,
        required: bool = False,
        ref=None,
        in_object: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.required = required
        self.is_array = is_array
        self.default_value = default_value
        self.predefined_values = predefined_values
        self.ref = ref
        self.type_ = type_
        self.in_ = in_
        self.in_object = in_object


class IntegrationGeneratorCommand:
    def __init__(
        self,
        name: str,
        url_path: str,
        http_method: str,
        description: Optional[str],
        arguments,
        outputs,
        context_path: str,
        root_object: str,
        headers: List[Dict[str, str]],
        unique_key: str,
        upload_file: bool = False,
        returns_file: bool = False,
        returns_entry_file: bool = False,
        body_format=None,
    ):
        self.name = name
        self.url_path = url_path
        self.http_method = http_method
        self.description = description
        self.context_path = context_path
        self.root_object = root_object
        self.headers = headers
        self.unique_key = unique_key
        self.body_format = body_format

        self.upload_file = upload_file
        self.returns_file = returns_file
        self.returns_entry_file = returns_entry_file

        if (
            isinstance(arguments, list)
            and len(arguments) > 0
            and isinstance(arguments[0], dict)
        ):
            self.arguments = [IntegrationGeneratorArg(**arg) for arg in arguments]
        else:
            self.arguments = arguments

        if (
            isinstance(outputs, list)
            and len(outputs) > 0
            and isinstance(outputs[0], dict)
        ):
            self.outputs = [IntegrationGeneratorOutput(**output) for output in outputs]
        else:
            self.outputs = outputs


class IntegrationGeneratorParam:
    def __init__(
        self,
        name: str,
        display: str,
        type_: Union[ParameterType, str],
        required: bool,
        defaultvalue: str = "",
        options: Optional[list] = None,
    ):
        self.name = name
        self.display = display
        self.defaultvalue = defaultvalue

        if isinstance(type_, ParameterType):
            self.type_: ParameterType = type_
        elif isinstance(type_, str):
            self.type_ = ParameterType[type_]

        self.required = required or False
        if options:
            self.options = options
        if defaultvalue:
            self.defaultvalue = defaultvalue
        if self.type_ == ParameterType.BOOLEAN and not self.defaultvalue:
            self.defaultvalue = "false"


class IntegrationGeneratorConfig:
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        params,
        category: str,
        command_prefix: str,
        commands,
        docker_image,
        url,
        base_url_path,
        auth,
        context_path,
        code_type="python",
        code_subtype="python3",
        is_fetch=False,
        fix_code=True,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.category = category
        self.command_prefix = command_prefix
        self.docker_image = docker_image
        self.url = url
        self.base_url_path = base_url_path or ""
        self.auth = auth
        self.context_path = context_path
        self.code_type = code_type or "python"
        self.code_subtype = code_subtype or "python3"
        self.is_fetch = is_fetch
        self.fix_code = fix_code

        if (
            commands
            and isinstance(commands, list)
            and len(commands) > 0
            and isinstance(commands[0], dict)
        ):
            self.commands = [
                IntegrationGeneratorCommand(**command) for command in commands
            ]
        else:
            self.commands = commands

        if isinstance(params, list) and len(params) > 0 and isinstance(params[0], dict):
            self.params = [IntegrationGeneratorParam(**param) for param in params]
        else:
            self.params = params

    def to_dict(self):
        return tools.to_dict(self)

    @staticmethod
    def get_arg_default(arg: IntegrationGeneratorArg) -> Optional[str]:
        """
        Gets the format for an argument default value, e.g.:
        >>> , ''
        >>> , False
        Args:
            arg: The argument to get the default format for.

        Returns:
            argument_default: The default format for the argument.
        """
        arg_type = ARGUMENT_TYPES.get(arg.type_, "str")
        if arg.default_value is None:
            return None

        if arg_type == "int":
            try:
                argument_default = f", {int(arg.default_value)}"
            except Exception:
                return None
        elif arg_type == "bool":
            try:
                argument_default = f", {strtobool(arg.default_value)}"
            except Exception:
                return None
        else:
            argument_default = f", '{arg.default_value}'"

        return argument_default

    @staticmethod
    def format_params(params: list, base: str, base_string: str) -> str:
        """
        Formats a list of params to a string of params assignment, e.g. param1=param_name, param2=param_name2
        Args:
            params: A list of params with mapping of name to code name
            base: The base code to use
            base_string: The base string to replace with the params

        Returns:
            params: Formatted params string
        """
        modified_params = []
        for p in params:
            for name, code_name in p.items():
                modified_params.append(f"{name}={code_name}")

        params_string = base.replace(base_string, ", ".join(modified_params))
        return params_string

    def generate_command_arguments(self, command: IntegrationGeneratorCommand) -> tuple:
        params_data = []
        body_data = []
        arguments = []
        argument_names = []
        arguments_found = False
        for arg in command.arguments:
            arguments_found = True
            code_arg_name = arg.name
            ref_arg_name = arg.name.lower()
            if arg.ref:
                ref_arg_name = f"{arg.ref}_{ref_arg_name}".lower()
                code_arg_name = f"{arg.ref}_{code_arg_name}".lower()

            if code_arg_name in ILLEGAL_CODE_NAMES:
                code_arg_name = f"{code_arg_name}{NAME_FIX}"

            new_arg_type: Optional[str] = None
            if arg.type_ == "array":
                argument_default: Optional[str] = ", []"
                new_arg_type = "argToList"
            elif arg.type_:
                new_arg_type = ARGUMENT_TYPES[arg.type_]
                if new_arg_type == "bool":
                    new_arg_type = "argToBoolean"
            else:
                argument_default = None

            if arg.default_value:
                argument_default = self.get_arg_default(arg)

            if argument_default:
                this_argument = f"{BASE_ARGUMENT.replace('$DARGNAME$', ref_arg_name)}{argument_default})"
            else:
                this_argument = f"{BASE_ARGUMENT.replace('$DARGNAME$', ref_arg_name)})"

            if new_arg_type:
                this_argument = (
                    this_argument.replace("$ARGTYPE$", f"{new_arg_type}(") + ")"
                )
            else:
                this_argument = this_argument.replace("$ARGTYPE$", "")

            code_arg_name = code_arg_name.lower()
            this_argument = this_argument.replace("$SARGNAME$", code_arg_name)
            argument_names.append(code_arg_name)
            arguments.append(this_argument)

            if arg.in_:
                if "query" in arg.in_:
                    params_data.append({arg.name: code_arg_name})
                elif arg.in_ in ["formData", "body"]:
                    body_data.append({arg.name: code_arg_name})

        return argument_names, arguments, arguments_found, body_data, params_data

    def generate_python_command_and_client_functions(
        self, command: IntegrationGeneratorCommand, is_api_key_in_query=False, auth=None
    ):
        function_name = command.name.replace("-", "_")
        headers = command.headers

        logger.info(f"Adding the function {function_name} to the code...")
        function = BASE_FUNCTION.replace("$FUNCTIONNAME$", function_name)
        req_function = BASE_REQUEST_FUNCTION.replace("$FUNCTIONNAME$", function_name)

        (
            argument_names,
            arguments,
            arguments_found,
            body_data,
            params_data,
        ) = self.generate_command_arguments(command)
        if arguments_found:
            function = function.replace("$ARGUMENTS$", "\n    ".join(arguments))
            function = function.replace("$REQARGS$", ", ".join(argument_names))
            req_function = req_function.replace("$REQARGS$", ", $REQARGS$")
            req_function = req_function.replace("$REQARGS$", ", ".join(argument_names))
        else:
            req_function = req_function.replace("$REQARGS$", "")
            function = function.replace("$REQARGS$", "")
            function = "\n".join(
                [x for x in function.split("\n") if "$ARGUMENTS$" not in x]
            )

        req_function = req_function.replace("$METHOD$", command.http_method)

        command.url_path = (
            f"'{command.url_path}'" if "'" not in command.url_path else command.url_path
        )
        command.url_path = (
            f"f{command.url_path}" if "{" in command.url_path else command.url_path
        )
        for param in re.findall(
            r"{([^}]+)}", command.url_path
        ):  # get content inside curly brackets
            if param in ILLEGAL_CODE_NAMES:
                command.url_path = command.url_path.replace(param, f"{param}{NAME_FIX}")
            command.url_path = command.url_path.replace(param, param.lower())

        req_function = req_function.replace("$PATH$", command.url_path)

        if is_api_key_in_query:
            if params_data is None:
                params_data = []

            api_key_name = list(
                filter(lambda x: "key" in x and x["key"] == "key", auth["apikey"])
            )[0]["value"]
            params_data.append({api_key_name: "self.api_key"})
        if params_data:
            params = self.format_params(params_data, BASE_PARAMS, "$PARAMS$")
            req_function = req_function.replace("$PARAMETERS$", params)
        else:
            req_function = "\n".join(
                [x for x in req_function.split("\n") if "$PARAMETERS$" not in x]
            )

        if body_data:
            body_code = json_body_to_code(command.body_format)
            req_function = req_function.replace("$DATA$", body_code)
        else:
            req_function = "\n".join(
                [x for x in req_function.split("\n") if "$DATA$" not in x]
            )

        if params_data:
            req_function = req_function.replace("$NEWPARAMS$", ", params=params")
        else:
            req_function = req_function.replace("$NEWPARAMS$", "")

        if body_data:
            req_function = req_function.replace("$NEWDATA$", ", json_data=data")
        else:
            req_function = req_function.replace("$NEWDATA$", "")

        if headers:
            new_headers = []
            for header in headers:
                for k, v in header.items():
                    new_headers.append(
                        BASE_HEADER.replace("$HEADERKEY$", f"'{k}'").replace(
                            "$HEADERVALUE$", f"'{v}'"
                        )
                    )

            req_function = req_function.replace(
                "$HEADERSOBJ$", " \n        ".join(new_headers)
            )
        else:
            req_function = "\n".join(
                [x for x in req_function.split("\n") if "$HEADERSOBJ$" not in x]
            )

        if self.context_path:
            context_name = self.context_path
        else:
            context_name = command.name.title().replace("_", "")

        if command.context_path:
            function = function.replace("$CONTEXTPATH$", f".{command.context_path}")
        else:
            function = function.replace("$CONTEXTPATH$", "")

        if command.root_object:
            function = function.replace(
                "$OUTPUTS$", f"response.get('{command.root_object}')"
            )
        else:
            function = function.replace("$OUTPUTS$", "response")

        if command.unique_key:
            function = function.replace("$UNIQUEKEY$", command.unique_key)
        else:
            function = function.replace("$UNIQUEKEY$", "")

        function = function.replace("$CONTEXTNAME$", context_name)

        return function, req_function

    def generate_integration_python_code(self):
        # Use the code from base_code in py as the basis
        code: str = BASE_CODE_TEMPLATE

        auth_api_key_in_query = False
        if self.auth:
            auth_method = self.auth["type"]

            if auth_method in ("apikey", "apiKey"):

                api_key_in = ""
                api_key_name = ""
                api_key_format = ""
                for item in self.auth["apikey"]:
                    if item["key"] == "in":
                        api_key_in = item["value"]
                    elif item["key"] == "key":
                        api_key_name = item["value"]
                    elif item["key"] == "format":
                        api_key_format = item["value"]

                if api_key_in == "query":
                    auth_api_key_in_query = True
                    code = code.replace("$CLIENT_API_KEY$", BASE_CLIENT_API_KEY)
                else:
                    # api key passed in header
                    if api_key_format:
                        code = code.replace(
                            "$BEARERAUTHPARAMS$",
                            BASE_HEADER_FORMATTED.replace(
                                "$HEADER_NAME$", api_key_name
                            ).replace("$HEADER_FORMAT$", api_key_format),
                        )
                    else:
                        code = code.replace(
                            "$BEARERAUTHPARAMS$",
                            BASE_HEADER_API_KEY.replace(
                                "$HEADER_API_KEY$", api_key_name
                            ),
                        )
            elif auth_method in "bearer":
                code = code.replace("$BEARERAUTHPARAMS$", BASE_BEARER_TOKEN)

            if auth_method in "basic":
                code = code.replace("$BASEAUTHPARAMS$", BASE_CREDENTIALS)
                code = code.replace("$BASEAUTH$", BASE_BASIC_AUTH)
            else:
                code = code.replace("$BASEAUTH$", "None")

            # code cleaning from different auth types
            code = code.replace("$BEARERAUTHPARAMS$", "")
            code = code.replace("$CLIENT_API_KEY$", "")
            code = code.replace("$BASEAUTHPARAMS$", "")

        # Build the functions from configuration file
        functions: list = []
        req_functions: list = []

        for command in self.commands:
            function, req_function = self.generate_python_command_and_client_functions(
                command, auth_api_key_in_query, self.auth
            )
            functions.append(function)
            req_functions.append(req_function)

        code = code.replace("$FUNCTIONS$", "\n".join(functions))
        code = code.replace("$BASEURL$", self.base_url_path)
        client = BASE_CLIENT.replace("$REQUESTFUNCS$", "".join(req_functions))
        code = code.replace("$CLIENT$", client)

        list_functions = []

        # Add the command mappings:
        for command in self.commands:
            prefix = f"{self.command_prefix}-" if self.command_prefix else ""

            if self.command_prefix:
                prefix = f"{self.command_prefix}-"

            function = BASE_LIST_FUNCTIONS.replace(
                "$FUNCTIONNAME$", f"{prefix}{command.name}".replace("_", "-")
            )
            fn = command.name.replace("-", "_")
            function = function.replace("$FUNCTIONCOMMAND$", f"{fn}_command")
            list_functions.append(function)

        code = code.replace("$COMMANDSLIST$", "\n\t".join(list_functions))
        logger.info("Finished generating the Python code.")

        if self.fix_code:
            logger.info("Fixing the code with autopep8...")

            code = autopep8.fix_code(
                code,
                options={
                    "max_line_length": 120,
                    "ignore": ["W293", "W504", "F405", "F403"],
                },
            )

        return code

    def get_yaml_commands(self) -> list:
        """
        Gets the integration commands in yaml format (in object representation) according to the configuration.

        Returns:
            commands: A list of integration commands in yaml format.
        """
        commands = []
        for command in self.commands:
            args = []
            for arg in command.arguments:
                options = None
                auto = None

                required = True if arg.required else False
                is_array = True if arg.type_ == "array" else False

                if arg.predefined_values:
                    auto = "PREDEFINED"
                    options = arg.predefined_values

                args.append(
                    XSOARIntegration.Script.Command.Argument(
                        name=arg.name.lower(),
                        description=arg.description or "",
                        required=required,
                        auto=auto,
                        predefined=options,
                        is_array=is_array,
                    )
                )

            outputs = []
            brand_context_path = self.context_path
            for output in command.outputs:
                output_name = output.name

                if command.context_path:
                    output_name = f"{command.context_path}.{output_name}"

                if brand_context_path:
                    output_name = f"{self.context_path}.{output_name}"

                outputs.append(
                    XSOARIntegration.Script.Command.Output(
                        output.type_, output_name, output.description
                    )
                )

            prefix = ""
            if self.command_prefix:
                prefix = f"{self.command_prefix}-"
            command_name = f"{prefix}{command.name}".replace("_", "-")
            commands.append(
                XSOARIntegration.Script.Command(
                    command_name, command.description, args, outputs
                )
            )

        return commands

    def get_yaml_params(self) -> list:
        """
        Gets the configuration params for the integration.

        Returns:
            params: A list of integration params.
        """
        params = []
        for param in self.params:
            params.append(
                XSOARIntegration.Configuration(
                    display=param.display,
                    name=param.name,
                    defaultvalue=param.defaultvalue,
                    type_=param.type_.value,
                    required=param.required,
                )
            )

        return params

    def generate_integration_yml(self, code: str = "") -> XSOARIntegration:
        """
        Generates the yaml structure of the integration.

        Returns:
            integration: An object representation of the integration yaml structure.

        """
        # Create the commands section
        commands = self.get_yaml_commands()
        commonfields = XSOARIntegration.CommonFields(self.name)
        name = self.name
        display = self.display_name
        category = self.category
        description = self.description
        configurations = self.get_yaml_params()

        script_object = XSOARIntegration.Script(
            type_=self.code_type,
            subtype=self.code_subtype,
            dockerimage=self.docker_image,
            isfetch=self.is_fetch,
            commands=commands,
            script=code,
        )

        integration = XSOARIntegration(
            commonfields=commonfields,
            name=name,
            display=display,
            category=category,
            description=description,
            configuration=configurations,
            script=script_object,
        )

        return integration

    def generate_integration_package(
        self, output_dir: Union[Path, str], is_unified: bool = False
    ):
        if is_unified:
            code = self.generate_integration_python_code()
            code = (
                code.replace("import demistomock as demisto", "")
                .replace("from CommonServerPython import *", "")
                .replace("from CommonServerUserPython import *", "")
            )

            xsoar_integration = self.generate_integration_yml(code)

            path = Path(output_dir, f"integration-{self.name}.yml")
            with open(path, mode="w") as f:
                yaml.dump(xsoar_integration.to_dict(), f)

                logger.info(f"Generated integration yml at:\n{os.path.abspath(path)}")

            return path

        package_dir = Path(output_dir, self.name)
        if not os.path.exists(package_dir):
            os.mkdir(package_dir)

        code = self.generate_integration_python_code()
        with open(Path(package_dir, f"{self.name}.py"), mode="w") as f:
            f.write(code)

        integration_obj = self.generate_integration_yml()
        try:
            logger.debug("Creating yml file...")
            with open(Path(package_dir, f"{self.name}.yml"), "w") as fp:
                yaml.dump(integration_obj.to_dict(), fp)

        except Exception as err:
            logger.exception(f"Failed to write integration yml file. Error: {err}")
            raise

        logger.info(
            f"Generated integration package at:\n{os.path.abspath(package_dir)}"
        )

import inspect
from typing import Any, Dict, Optional, Union, get_args, get_origin

import click
from colorama import Fore

from demisto_sdk.commands.common import constants, errors

TEMPLATE = """
Error Code: {code}
Function: {func}
Ignorable: {ignorable}
Message:
{msg}
"""


TYPE_FILLER_MAPPING = {
    int: 1337,
    bool: True,
    dict: {"key1": "value1", "key2": "value2"},
    Dict: {"key1": "value1", "key2": "value2"},
    list: ["element1", "element2"],
    constants.FileType: constants.FileType.INTEGRATION,
}


def parse_function_parameters(sig: inspect.Signature):
    parameters = {}
    for param in sig.parameters.values():
        value: Any = f"<{param.name}>"
        if param.default is not inspect.Parameter.empty:
            value = param.default

        if param.annotation is not inspect.Parameter.empty:
            param_type = param.annotation
            if get_origin(param.annotation) in [Union, Optional]:
                param_type = get_args(param.annotation)[0]

            if param_type is not str:
                value = TYPE_FILLER_MAPPING.get(param_type) or param_type()

        parameters[param.name] = value

    return parameters


def print_error_information(func_name, error_data, func, sig: inspect.Signature):
    parameters = parse_function_parameters(sig)

    click.secho(f"{Fore.GREEN}## Error Code Info ##{Fore.RESET}")
    click.secho(
        TEMPLATE.format(
            code=error_data["code"],
            func=f"{func_name}{sig}",
            ignorable=error_data["code"] in errors.ALLOWED_IGNORE_ERRORS,
            msg=func(**parameters)[0],
        )
    )


def find_error(error_code):
    for func_name, error_data in errors.ERROR_CODE.items():
        if error_data["code"] == error_code:
            return func_name, error_data

    return "", {}


def generate_error_code_information(error_code):
    func_name, error_data = find_error(error_code)
    if not func_name:
        click.secho(f"{Fore.RED}No such error")
        return 1

    func = getattr(errors.Errors, func_name)
    sig = inspect.signature(func)

    print_error_information(func_name, error_data, func, sig)
    return 0

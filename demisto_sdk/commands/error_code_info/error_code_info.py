import inspect
from typing import Any, Dict, List, Literal, Optional, Union, get_args, get_origin

from more_itertools import map_reduce

from demisto_sdk.commands.common import constants, errors
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.validate.validators.base_validator import get_all_validators

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
    List[str]: ["element1", "element2"],
    constants.FileType: constants.FileType.INTEGRATION,
}


def parse_legacy_function_parameters(sig: inspect.Signature):
    parameters = {}
    for param in sig.parameters.values():
        value: Any = f"<{param.name}>"
        if param.default is not inspect.Parameter.empty:
            value = param.default

        if param.annotation is not inspect.Parameter.empty:
            param_type = param.annotation
            if get_origin(param.annotation) in [Union, Optional]:
                param_type = get_args(param.annotation)[0]

            # param_type = str or param_type = "Optional[Type]" or param_type = "Union[Type1, Type2]"
            if param_type is not str and not isinstance(param_type, str):
                value = TYPE_FILLER_MAPPING.get(param_type) or param_type()

        parameters[param.name] = value

    return parameters


def print_legacy_error_information(func_name, error_data, func, sig: inspect.Signature):
    parameters = parse_legacy_function_parameters(sig)

    logger.info("<green>## Error Code Info ##</green>")
    logger.info(
        TEMPLATE.format(
            code=error_data["code"],
            func=f"{func_name}{sig}",
            ignorable=error_data["code"] in errors.ALLOWED_IGNORE_ERRORS,
            msg=func(**parameters)[0],
        )
    )


def find_legacy_error(error_code):
    for func_name, error_data in errors.ERROR_CODE.items():
        if error_data["code"] == error_code:
            return func_name, error_data

    return "", {}


def generate_legacy_error_code_information(error_code):
    func_name, error_data = find_legacy_error(error_code)
    if not func_name:
        logger.info("<red>No such error</red>")
        return 1

    func = getattr(errors.Errors, func_name)
    sig = inspect.signature(func)

    print_legacy_error_information(func_name, error_data, func, sig)
    return 0


def print_error_info(error_code: str) -> Union[Literal[0], Literal[1]]:
    """
    Tries to print info of a BaseValidator-based class validation.
    If there isn't one for the given code, uses legacy code that prints from errors.py, instead.
    """
    code_to_validators = map_reduce(
        get_all_validators(), lambda validator: validator.error_code
    )

    if validators := code_to_validators.get(error_code):
        for validator in validators:
            is_autofix = (
                "Autofixable" if validator.is_auto_fixable else "Not Autofixable"
            )
            logger.info(
                "\n".join(
                    (
                        f"{k}\t{v}"
                        for k, v in (
                            ("Error Code", f"{error_code} ({is_autofix})"),
                            ("Description", validator.description),
                            ("Rationale", validator.rationale),
                        )
                    )
                )
            )
        return 0
    else:
        logger.debug(
            f"Could not find a BaseValidator-inheriting class for {error_code}, "
            "using legacy `error-code` command instead."
        )
        return generate_legacy_error_code_information(error_code)

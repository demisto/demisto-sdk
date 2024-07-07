import os
from typing import List, Union

import typer

CI_ENV_VAR = "CI"
ERROR_IS_CI_INVALID = (
    "Invalid value for CI env var. Expected 'true' or 'false', actual '{env_var_str}'"
)
ERROR_INPUT_FILES_INVALID = "Invalid value for input files: {input}"
HELP_CHANGED_FILES = "The files to check, e.g. dir/f1 f2 f3.py"


def split_files(files_str: Union[str, List[str]]) -> List[str]:
    """
    Helper function to return a `list` of `str`
    from an input string.

    Args:
    - `files_str` (``str | List[str]``): The input files.

    Returns
    - `List[str]` containing a list of strings.
    """

    if isinstance(files_str, list):
        return files_str
    elif isinstance(files_str, str):
        return files_str.split() if files_str else []
    else:
        raise typer.BadParameter(ERROR_INPUT_FILES_INVALID.format(input=files_str))


def is_ci() -> bool:
    """
    Helper function to detect whether we're running
    in a CI environment. To detect this, we rely on the `CI` env var.

    Returns:
    - `True` if we're in a CI environment, `False` otherwise.
    """

    if os.getenv(CI_ENV_VAR):
        env_var_str = os.getenv(CI_ENV_VAR, "false").lower()
        if env_var_str in {"true", "1", "yes"}:
            return True
        elif env_var_str in {"false", "0", "no"}:
            return False
        else:
            raise typer.BadParameter(
                ERROR_IS_CI_INVALID.format(env_var_str=env_var_str)
            )
    else:
        return False

from typing import Any, Optional

from demisto_sdk.commands.common.constants import STRING_TO_BOOL_MAP


def string_to_bool(
    input_: Any,
    default_when_empty: Optional[bool] = None,
) -> bool:
    """
    This function is its own file (rather than in `tools.py`) to avoid circular imports:
    string_to_bool is used in the logger setup, which imports `tools.py`, where we have functions importing the logger
    """
    try:
        return STRING_TO_BOOL_MAP[str(input_).lower()]
    except (KeyError, TypeError):
        if input_ in ("", None) and default_when_empty is not None:
            return default_when_empty

    raise ValueError(f"cannot convert {input_} to bool")

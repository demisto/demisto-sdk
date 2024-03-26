import inspect
from typing import Dict, List, Union

from demisto_sdk.commands.error_code_info import error_code_info


def test_parse_function_parameters():
    def dummy_func(
        param1: str, param2: Dict, param3: Union[str, List], param4: int = 0
    ):
        return f"error with {param1}, {param2.items()}, {param3}, {param4 + 1}", 1234

    sig = inspect.signature(dummy_func)
    parameters = error_code_info.parse_function_parameters(sig)

    assert parameters["param1"] == "<param1>"
    assert parameters["param2"] == error_code_info.TYPE_FILLER_MAPPING[dict]
    assert parameters["param3"] == "<param3>"
    assert parameters["param4"] == error_code_info.TYPE_FILLER_MAPPING[int]

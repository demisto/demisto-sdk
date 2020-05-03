import pytest
from demisto_sdk.commands.common.hook_validations.utils import is_v2_file

V2_VALID_1 = {"display": "integrationname v2", "name": "integrationname v2", "id": "integrationname v2"}
V2_WRONG_DISPLAY = {"display": "integrationname V2", "name": "integrationv2name", "id": "integrationname V2"}
V2_VALID_2 = {"display": "integrationnameV2", "name": "integrationnameV2", "id": "integrationnameV2"}
V2_NAME_INPUTS = [
    (V2_VALID_1, True),
    (V2_WRONG_DISPLAY, False),
    (V2_VALID_2, True),
]


@pytest.mark.parametrize("current, answer", V2_NAME_INPUTS)
def test_is_v2_file(current, answer):
    assert is_v2_file(current) is answer

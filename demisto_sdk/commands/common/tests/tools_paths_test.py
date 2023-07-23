import pytest

from demisto_sdk.commands.common.tools_paths import string_to_bool


@pytest.mark.parametrize("value", ("true", "True", 1, "1", "yes", "y"))
def test_string_to_bool_true(value: str):
    assert string_to_bool(value)


@pytest.mark.parametrize("value", ("", None))
def test_string_to_bool_default_true(value: str):
    assert string_to_bool(value, True)


@pytest.mark.parametrize("value", ("false", "False", 0, "0", "n", "no"))
def test_string_to_bool_false(value: str):
    assert not string_to_bool(value)


@pytest.mark.parametrize("value", ("", " ", "כן", None, "None"))
def test_string_to_bool_error(value: str):
    with pytest.raises(ValueError):
        string_to_bool(value)

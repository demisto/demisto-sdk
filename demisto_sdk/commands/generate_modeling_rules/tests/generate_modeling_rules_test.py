import pytest

from demisto_sdk.commands.generate_modeling_rules.generate_modeling_rules import (
    array_create,
    convert_raw_type_to_xdm_type,
    convert_to_xdm_type,
    create_xif_header,
    extract_raw_type_data,
    json_extract_array,
    json_extract_scalar,
    replace_last_char,
    to_number,
    to_string,
)


@pytest.mark.parametrize("s, res", (["hello,\n", "hello;\n"], ["", ""]))
def test_replace_last_char(s, res):
    assert replace_last_char(s) == res


def test_create_xif_header(mocker):
    res = "[MODEL: dataset=blabla]\n" "| alter\n"
    assert create_xif_header("blabla") == res


@pytest.mark.parametrize(
    "input, res", (["string", "String"], ["int", "Number"], ["ggg", "String"])
)
def test_convert_raw_type_to_xdm_type(input, res):
    assert convert_raw_type_to_xdm_type(input) == res


@pytest.mark.parametrize(
    "path, res",
    (
        ["hello", ("string", False)],
        ["test.bla", ("int", False)],
        ["test.gg.hh", ("string", True)],
        ["arr", ("string", True)],
        ["y.j", ("string", False)],
        ["t", ("string", False)],
        ["r", ("string", False)],
    ),
)
def test_extract_raw_type_data(path, res):
    event = {
        "hello": "hello",
        "test": {"bla": 3, "gg": {"hh": [5, 6]}},
        "arr": [True, False, False],
        "y": {"j": {"h": "k"}},
        "t": None,
    }
    assert extract_raw_type_data(event, path) == res


def test_extract_raw_type_data_empty_event():
    event: dict = {}
    with pytest.raises(ValueError):
        extract_raw_type_data(event, "bla")


def test_extract_raw_type_data_event_not_dict():
    event = True
    with pytest.raises(ValueError):
        extract_raw_type_data(event, "bbb")


def test_json_extract_array():
    assert (
        json_extract_array("prefix", "suffix")
        == 'json_extract_array(prefix, "$.suffix")'
    )


def test_json_extract_scalar():
    assert (
        json_extract_scalar("prefix", "suffix")
        == 'json_extract_scalar(prefix, "$.suffix")'
    )


def test_array_create():
    assert array_create("test") == "arraycreate(test)"


def test_to_string():
    assert to_string("test") == "to_string(test)"


def test_to_number():
    assert to_number("6") == "to_number(6)"


@pytest.mark.parametrize(
    "name, xdm_type, res",
    (["test", "String", "to_string(test)"], ["6", "Number", "to_number(6)"]),
)
def test_convert_to_xdm_type(name, xdm_type, res):
    assert convert_to_xdm_type(name, xdm_type) == res

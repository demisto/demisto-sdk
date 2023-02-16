import pytest

from demisto_sdk.commands.generate_modeling_rules.generate_modeling_rules import (
    array_create_wrap,
    convert_raw_type_to_xdm_type,
    convert_to_xdm_type,
    create_xif_header,
    extract_raw_type_data,
    json_extract_array_wrap,
    json_extract_scalar_wrap,
    replace_last_char,
    to_number_wrap,
    to_string_wrap,
)


@pytest.mark.parametrize("s, res", (["hello,\n", "hello;\n"], ["", ""]))
def test_replace_last_char(s, res):
    """
    Given:
        A line that ends with ,\n

    When:
        We are at the last line of the xif file 

    Then:
        replace the second last char with ;
    """
    assert replace_last_char(s) == res


def test_create_xif_header(mocker):
    """
    Given:
        A dataset name

    When:
        creating the header of the xif file.

    Then:
        check that the header is formed corectlly. 
    """
    res = "[MODEL: dataset=fake_dataset_name]\n" "| alter\n"
    assert create_xif_header("fake_dataset_name") == res


@pytest.mark.parametrize(
    "input, res", (["string", "String"], ["int", "Number"], ["ggg", "String"])
)
def test_convert_raw_type_to_xdm_type(input, res):
    """
    Given:
        value type of the raw event.

    When:
        checking if we will need to wrap with some casting function.

    Then:
        check that the conversion was done properly.
    """
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
    """
    Given:
        - A path to a field of a dict with '.' to state hirarchy.

    When:
        - parsing the event to check its types and they are valid.

    Then:
        - check that we get the correct answer in the form of (type, isArray).
    """
    event = {
        "hello": "hello",
        "test": {"bla": 3, "gg": {"hh": [5, 6]}},
        "arr": [True, False, False],
        "y": {"j": {"h": "k"}},
        "t": None,
    }
    assert extract_raw_type_data(event, path) == res


def test_extract_raw_type_data_empty_event():
    """
    Given:
        - A path to a field of a dict with '.' to state hirarchy.

    When:
        - parsing the event to check its types and its not a dictionary (as expected).

    Then:
        - validate that an error is raised.
    """
    event: dict = {}
    with pytest.raises(ValueError):
        extract_raw_type_data(event, "bla")


def test_extract_raw_type_data_event_not_dict():
    """
    Given:
        - A path to a field of a dict with '.' to state hirarchy.

    When:
        - parsing the event to check its types and its not a dictionary (as expected).

    Then:
        - check that we get the correct answer in the form of (type, isArray).
    """
    event = True
    with pytest.raises(ValueError):
        extract_raw_type_data(event, "bbb")


def test_json_extract_array_wrap():
    assert (
        json_extract_array_wrap("prefix", "suffix")
        == 'json_extract_array(prefix, "$.suffix")'
    )


def test_json_extract_scalar_wrap():
    """
    Test the json_extract_scalar wrapper
    """
    assert (
        json_extract_scalar_wrap("prefix", "suffix")
        == 'json_extract_scalar(prefix, "$.suffix")'
    )


def test_array_create_wrap():
    """
    Test the array_create wrapper
    """
    assert array_create_wrap("test") == "arraycreate(test)"


def test_to_string_wrap():
    assert to_string_wrap("test") == "to_string(test)"


def test_to_number_wrap():
    """
    Test the to_number wrapper
    """
    assert to_number_wrap("6") == "to_number(6)"


@pytest.mark.parametrize(
    "name, xdm_type, res",
    (["test", "String", "to_string(test)"], ["6", "Number", "to_number(6)"]),
)
def test_convert_to_xdm_type(name, xdm_type, res):
    assert convert_to_xdm_type(name, xdm_type) == res

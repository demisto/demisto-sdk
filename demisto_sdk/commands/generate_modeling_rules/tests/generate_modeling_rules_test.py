import tempfile
from pathlib import Path

import pytest

from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.generate_modeling_rules.generate_modeling_rules import (
    MappingField,
    RawEventData,
    array_create_wrap,
    coalesce_wrap,
    convert_raw_type_to_xdm_type,
    convert_to_xdm_type,
    create_xif_file,
    create_xif_header,
    create_yml_file,
    extract_data_from_all_xdm_schema,
    extract_raw_type_data,
    handle_raw_evnet_data,
    init_mapping_field_list,
    json_extract_array_wrap,
    json_extract_scalar_wrap,
    read_mapping_file,
    replace_last_char,
    snake_to_camel_case,
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


def test_create_xif_header():
    """
    Given:
        A dataset name

    When:
        creating the header of the xif file.

    Then:
        check that the header is formed corectlly.
    """
    res = "[MODEL: dataset=fake_dataset_name]\nalter\n"
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


def test_extract_data_from_all_xdm_schema():
    xdm_rule_to_dtype = {
        "_insert_time": "Timestamp",
        "_time": "Timestamp",
        "_vendor": "String",
        "_product": "String",
        "xdm.session_context_id": "String",
    }
    xdm_rule_to_dclass = {
        "_insert_time": "Scalar",
        "_time": "Scalar",
        "_vendor": "Scalar",
        "_product": "Scalar",
        "xdm.session_context_id": "Scalar",
    }
    schema_path = Path(__file__).parent / "test_data/Schema.csv"
    assert extract_data_from_all_xdm_schema(schema_path) == (
        xdm_rule_to_dtype,
        xdm_rule_to_dclass,
    )


def test_read_mapping_file():
    mapping_file_path = (
        Path(__file__).parent / "test_data/mapping_dfender_for_cloud.csv"
    )
    name_columen = [
        "id",
        "name",
        "properties.alertDisplayName",
        "properties.alertType",
        "properties.compromisedEntity",
        "properties.description",
        "properties.entities",
        "properties.entities.address",
    ]
    xdm_one_data_model = [
        "xdm.observer.unique_identifier",
        "xdm.observer.name",
        "xdm.alert.name",
        "xdm.alert.category",
        "xdm.target.host.hostname",
        "xdm.alert.description",
        "",
        "xdm.target.host.ipv4_addresses",
    ]
    assert read_mapping_file(mapping_file_path) == (name_columen, xdm_one_data_model)


def test_read_mapping_file_invalid_header_names():
    mapping_file_path = Path(__file__).parent / "test_data/mapping_invalid_headers.csv"
    with pytest.raises(NameError):
        read_mapping_file(mapping_file_path)
    assert mapping_file_path


def test_create_yml_file():
    result_yml_path = Path(__file__).parent / "test_data/result_create_yml_file.yml"

    with tempfile.TemporaryDirectory() as tmpdirname:
        created_yml_path = Path(tmpdirname, "test_test_modeling_rules.yml")
        create_yml_file(created_yml_path, "test", "test")
        with open(created_yml_path) as f:
            yml_created = yaml.load(f)

    with open(result_yml_path) as f:
        yml_result = yaml.load(result_yml_path)

    assert yml_created == yml_result


def test_snake_to_camel_case():
    assert snake_to_camel_case("hello_world") == "HelloWorld"
    assert snake_to_camel_case("this_is_a_long_string") == "ThisIsALongString"
    assert snake_to_camel_case("") == ""


def test_coalesce_wrap():
    """
    Given:
        - A list of data on raw event fields
    When:
        - More than one field is assigned to an XDM rule coalesce
    Then:
        - Make and return a coalesce expression"""
    list_of_mapping = ["hello", "how", "are", "you"]
    assert coalesce_wrap(list_of_mapping) == "coalesce(hello, how, are, you)"


def test_handle_raw_evnet_data():
    """
    Given:
        - A '|' seperated str of raw event paths.
    When:
        - parsing the modeling rule schema file.
    Then:
        - Return a list of RawEventData objects
    """
    event = {
        "hello": "hello",
        "test": {"bla": 3, "gg": {"hh": [5, 6]}},
        "arr": [True, False, False],
        "y": {"j": {"h": "k"}},
        "t": None,
    }
    res = handle_raw_evnet_data("test.gg.hh | hello", event)
    assert res == [
        RawEventData("test.gg.hh", is_array_raw=True, type_raw="string"),
        RawEventData("hello", is_array_raw=False, type_raw="string"),
    ]


def test_create_xif_file():
    """
    Given:
        - A mapping that.
    When:
        - Creating an xif file.
    Then:
        - Make sure that the xif file is generated correctlly.
    """
    result_xif_path = Path(__file__).parent / "test_data/test1_create_xif_file.xif"
    mf = MappingField(
        "xdm.event.type",
        "String",
        "Scalar",
        [RawEventData("test.bla", is_array_raw=True, type_raw="int")],
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        created_xif_path = Path(tmpdirname, "test_test_xif_file.xif")
        create_xif_file([mf], created_xif_path, "test_test")
        created_xif_file_res = Path(created_xif_path).read_text()
    xif_result = Path(result_xif_path).read_text()
    assert xif_result == created_xif_file_res


def test_create_xif_file_coalesce():
    """
    Given:
        - A mapping that.
    When:
        - The mapping contains 2 raw paths to the same xdm rule.
    Then:
        - Make sure that the generated xif file if correct and has the coalesce
    """
    result_xif_path = Path(__file__).parent / "test_data/test2_create_xif_file.xif"
    mf = MappingField(
        "xdm.event.type",
        "String",
        "Scalar",
        [
            RawEventData("test.bla", is_array_raw=True, type_raw="int"),
            RawEventData("check", is_array_raw=False, type_raw="string"),
        ],
    )
    with tempfile.TemporaryDirectory() as tmpdirname:
        created_xif_path = Path(tmpdirname, "test_test_xif_file.xif")
        create_xif_file([mf], created_xif_path, "test_test")
        created_xif_file_res = Path(created_xif_path).read_text()
    xif_result = Path(result_xif_path).read_text()
    assert xif_result == created_xif_file_res


def test_init_mapping_field_list(mocker):
    """
    Given:
        - All the data to generate the Mapping field object
    When:
        - One of the specified xdm field in the mapping does not exist in the xdm onedata model
    Then:
        - Make sure the user gets an informative message
    """
    name_columen = ["ip", "address", "domain"]
    xdm_one_data_model = ["xdm_rule1", "xdm_rule4", "xdm_rule3"]
    raw_event: dict = {}
    xdm_rule_to_dtype = {
        "xdm_rule1": "type1",
        "xdm_rule2": "type2",
        "xdm_rule3": "type3",
    }
    xdm_rule_to_dclass = {
        "xdm_rule1": "Sclar",
        "xdm_rule2": "Array",
        "xdm_rule3": "Scalar",
    }
    handle_raw_evnet_data_mock = mocker.patch(
        "demisto_sdk.commands.generate_modeling_rules.generate_modeling_rules.handle_raw_evnet_data"
    )
    handle_raw_evnet_data_mock.return_value = [
        RawEventData("test.bla", is_array_raw=True, type_raw="int"),
        RawEventData("check", is_array_raw=False, type_raw="string"),
    ]
    with pytest.raises(ValueError):
        init_mapping_field_list(
            name_columen,
            xdm_one_data_model,
            raw_event,
            xdm_rule_to_dtype,
            xdm_rule_to_dclass,
        )

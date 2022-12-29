from pathlib import Path
from typing import Optional

import pytest

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import run_command
from demisto_sdk.commands.generate_outputs.json_to_outputs.json_to_outputs import (
    determine_type,
    json_to_outputs,
    parse_json,
)

json = JSON_Handler()


DUMMY_FIELD_DESCRIPTION = "dummy field description"
TEST_PATH = Path("demisto_sdk/commands/generate_outputs/json_to_outputs/tests")


def git_path() -> str:
    path = run_command("git rev-parse --show-toplevel")
    return path.replace("\n", "")


def test_json_to_outputs__json_from_file():
    """
        Given
            - valid json file: {"aaa":100,"bbb":"foo"}
            - prefix: XDR.Incident
            - command: xdr-get-incidents
        When
            - passed to json_to_outputs
        Then
            - ensure outputs generated in the following format

    arguments: []
    name: xdr-get-incidents
    outputs:
    - contextPath: XDR.Incident.aaa
      description: ''
      type: Number
    - contextPath: XDR.Incident.bbb
      description: ''
      type: String

    """
    yaml_output = parse_json(
        data='{"aaa":100,"bbb":"foo"}',
        command_name="xdr-get-incidents",
        prefix="XDR.Incident",
    )

    assert (
        yaml_output
        == """arguments: []
name: xdr-get-incidents
outputs:
- contextPath: XDR.Incident.aaa
  description: ''
  type: Number
- contextPath: XDR.Incident.bbb
  description: ''
  type: String
"""
    )


def test_json_to_outputs__invalid_json():
    """
    Given
        - invalid json file {"aaa":100
    When
        - passed to json_to_outputs
    Then
        - ensure the function raises clear error that indicates that json is invalid

    """
    try:
        parse_json(
            data='{"aaa":100', command_name="xdr-get-incidents", prefix="XDR.Incident"
        )

        assert False
    except Exception as ex:
        assert str(ex) == "Invalid input JSON"


DATETIME_MIN_VALUES = [
    "0001-01-01T00:00:00",
    "0001-01-01T00:00",
    "0001-01-01Z00:00:00",
    "0001-01-01Z00:00",
]


@pytest.mark.parametrize("time_created", ["2019-10-10T00:00:00"] + DATETIME_MIN_VALUES)
def test_json_to_outputs__detect_date(time_created):
    """
    Given
        - valid json {"create_at": "2019-10-10T00:00:00"}
    When
        - passed to json_to_outputs
    Then
        - ensure the type of create_at is Date

    """
    yaml_output = parse_json(
        data=json.dumps({"created_at": time_created}),
        command_name="jira-ticket",
        prefix="Jira.Ticket",
        descriptions={"created_at": "time when the ticket was created."},
    )

    assert (
        yaml_output
        == """arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.created_at
  description: time when the ticket was created.
  type: Date
"""
    )


def test_json_to_outputs__a_list_of_dict():
    """
    Given
        - A list of dictionaries
    When
        - Passed to json_to_outputs
    Then
        - ensure the returned type is correct
    """
    yaml_output = parse_json(
        data='[{"a": "b", "c": "d"}, {"a": 1}]',
        command_name="jira-ticket",
        prefix="Jira.Ticket",
        descriptions={"a": DUMMY_FIELD_DESCRIPTION},
    )

    assert (
        yaml_output
        == f"""arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.a
  description: {DUMMY_FIELD_DESCRIPTION}
  type: Number
- contextPath: Jira.Ticket.c
  description: ''
  type: String
"""
    )


@pytest.mark.parametrize(
    "description_dictionary, expected_a_description",
    [
        ({}, "''"),
        ({"nonexistent_field": "foo"}, "''"),
        (None, "''"),
        ("", "''"),
        ({"q": "this should not show as q is not in the data"}, "''"),
    ],
)
def test_json_to_outputs__invalid_description_dictionary(
    description_dictionary, expected_a_description
):
    """
    Given
        - A list of dictionaries
    When
        - Passed to json_to_outputs
    Then
        - ensure the returned type is correct
    """
    yaml_output = parse_json(
        data='[{"a": "b", "c": "d"}, {"a": 1}]',
        command_name="jira-ticket",
        prefix="Jira.Ticket",
        descriptions=description_dictionary,
    )

    assert (
        yaml_output
        == f"""arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.a
  description: {expected_a_description}
  type: Number
- contextPath: Jira.Ticket.c
  description: ''
  type: String
"""
    )


def test_json_to_outputs_return_object():
    """
    Given
        - valid json file: {"aaa":100,"bbb":"foo"}
        - prefix: XDR.Incident
        - command: xdr-get-incidents
    When
        - passed to json_to_outputs with return_object=True
    Then
        - ensure outputs generated aer a pythonic object and not yaml

    arguments: []
    name: xdr-get-incidents
    outputs:
    - contextPath: XDR.Incident.aaa
      description: ''
      type: Number
    - contextPath: XDR.Incident.bbb
      description: ''
      type: String

    """
    yaml_output = parse_json(
        data='{"aaa":100,"bbb":"foo"}',
        command_name="xdr-get-incidents",
        prefix="XDR.Incident",
        return_object=True,
    )

    assert yaml_output == {
        "arguments": [],
        "name": "xdr-get-incidents",
        "outputs": [
            {"contextPath": "XDR.Incident.aaa", "description": "", "type": "Number"},
            {"contextPath": "XDR.Incident.bbb", "description": "", "type": "String"},
        ],
    }


dummy_description_dictionary = {
    "day": "day of the week",
    "color": "assigned color",
    "surprise": "a value that should not appear in the result.",
}
dummy_integration_output = {"day": "Sunday", "color": "Blue"}


@pytest.mark.parametrize(
    "description_argument,dictionary",
    [
        # no description_dictionary
        (None, dict()),
        # description_dictionary from mock input
        ("not_a_json_string", dict()),
        # description dictionary from argument
        (json.dumps(dummy_description_dictionary), dummy_description_dictionary),
    ],
)
def test_json_to_outputs__description_dictionary(
    tmpdir, description_argument: Optional[str], dictionary: dict
):
    """
    Given
        - a (possibly-empty) JSON description dictionary
    When
        - Passed to json_to_outputs
    Then
        - ensure the returned values are correct
    """

    output = tmpdir.join("test_json_to_outputs__file_input.yml")
    temp_json_input_path = tmpdir.join("dummy_integration_output.json")

    temp_json_input_path.write(json.dumps(dummy_integration_output))

    json_to_outputs(
        command="jsonToOutputs",
        json=str(temp_json_input_path),
        prefix="Test",
        output=output,
        descriptions=description_argument,
    )

    assert (
        output.read()
        == f"""arguments: []
name: jsonToOutputs
outputs:
- contextPath: Test.day
  description: {dictionary.get('day', "''")}
  type: String
- contextPath: Test.color
  description: {dictionary.get('color', "''")}
  type: String
"""
    )


def test_json_to_outputs__description_file(tmpdir):
    """
    Given
        - A path to a integration output JSON
        - A path to a dictionary-description JSON
    When
        - Passed to json_to_outputs
    Then
        - ensure the returned values are correct
    """

    output = tmpdir.join("test_json_to_outputs__file_input.yml")

    temp_json_input_path = tmpdir.join("dummy_integration_output.json")
    temp_json_input_path.write(json.dumps(dummy_integration_output))

    dictionary = dummy_description_dictionary

    temp_description_file = tmpdir.join("description_file.json")
    temp_description_file.write(json.dumps(dummy_description_dictionary))

    json_to_outputs(
        command="jsonToOutputs",
        json=str(temp_json_input_path),
        prefix="Test",
        output=output,
        descriptions=temp_description_file,
    )

    assert (
        output.read()
        == f"""arguments: []
name: jsonToOutputs
outputs:
- contextPath: Test.day
  description: {dictionary.get('day', "''")}
  type: String
- contextPath: Test.color
  description: {dictionary.get('color', "''")}
  type: String
"""
    )


INPUT = [
    (True, "Boolean"),
    (0, "Number"),
    (1, "Number"),
    (False, "Boolean"),
    ("test string", "String"),
]


@pytest.mark.parametrize("value, type", INPUT)
def test_determine_type(value, type):
    """
    Given
        - value of the dict.
    When
        - determine type function runs
    Then
        - ensure the returned type is correct
    """
    assert determine_type(value) == type

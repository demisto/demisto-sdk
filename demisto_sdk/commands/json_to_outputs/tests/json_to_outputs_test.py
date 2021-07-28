import json
from typing import Optional

import pytest

from demisto_sdk.commands.json_to_outputs.json_to_outputs import (
    determine_type, json_to_outputs, parse_json)

DUMMY_FIELD_DESCRIPTION = "dummy field description"


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
        command_name='xdr-get-incidents',
        prefix='XDR.Incident'
    )

    assert yaml_output == '''arguments: []
name: xdr-get-incidents
outputs:
- contextPath: XDR.Incident.aaa
  description: ''
  type: Number
- contextPath: XDR.Incident.bbb
  description: ''
  type: String
'''


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
            data='{"aaa":100',
            command_name='xdr-get-incidents',
            prefix='XDR.Incident'
        )

        assert False
    except Exception as ex:
        assert str(ex) == 'Invalid input JSON'


def test_json_to_outputs__detect_date():
    """
    Given
        - valid json {"create_at": "2019-10-10T00:00:00"}
    When
        - passed to json_to_outputs
    Then
        - ensure the type of create_at is Date

    """
    yaml_output = parse_json(
        data='{"created_at": "2019-10-10T00:00:00"}',
        command_name='jira-ticket',
        prefix='Jira.Ticket',
        description_dictionary={'created_at': 'time when the ticket was created.'}
    )

    assert yaml_output == '''arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.created_at
  description: time when the ticket was created.
  type: Date
'''


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
        command_name='jira-ticket',
        prefix='Jira.Ticket',
        description_dictionary={"a": DUMMY_FIELD_DESCRIPTION}
    )

    assert yaml_output == f'''arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.a
  description: {DUMMY_FIELD_DESCRIPTION}
  type: Number
- contextPath: Jira.Ticket.c
  description: ''
  type: String
'''


@pytest.mark.parametrize('description_dictionary, expected_a_description',
                         [
                             ({}, "''"),
                             ({'nonexistent_field': 'foo'}, "''"),
                             (None, "''"),
                             ("", "''"),
                             ({"q": "this should not show as q is not in the data"}, "''")
                         ])
def test_json_to_outputs__empty_description_dictionary(description_dictionary, expected_a_description):
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
        command_name='jira-ticket',
        prefix='Jira.Ticket',
        description_dictionary=description_dictionary
    )

    assert yaml_output == f'''arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.a
  description: {expected_a_description}
  type: Number
- contextPath: Jira.Ticket.c
  description: ''
  type: String
'''


# this is the content of `dummy_description_dictionary.json`
dummy_description_dictionary = {"day": "day of the week",
                                "color": "assigned color",
                                "surprise": "a value that should not appear in the result."}


@pytest.mark.parametrize('description_argument,dictionary',
                         [(None, dict()),
                          ("true", dict()),  # takes descriptions from mock input
                          (json.dumps(dummy_description_dictionary), dummy_description_dictionary),  # basic test
                          ('dummy_description_dictionary.json', dummy_description_dictionary)  # JSON file path
                          ])
def test_json_to_outputs__description(mocker, tmpdir, description_argument: Optional[str], dictionary: dict):
    output = tmpdir.join("test_json_to_outputs__file_input.yml")

    mocker.patch('demisto_sdk.commands.json_to_outputs.json_to_outputs.input_multiline',
                 return_value=dummy_description_dictionary)

    json_to_outputs(command='jsonToOutputs',
                    input='dummy_integration_output.json',
                    prefix='Test',
                    output=output,
                    descriptions=description_argument)

    with open(output) as f:
        assert f.read() == f"""arguments: []
name: jsonToOutputs
outputs:
- contextPath: Test.day
  description: {dictionary.get('day', "''")}
  type: String
- contextPath: Test.color
  description: {dictionary.get('color', "''")}
  type: String
"""


INPUT = [(True, 'Boolean'),
         (0, 'Number'),
         (1, 'Number'),
         (False, 'Boolean'),
         ("test string", 'String')]


@pytest.mark.parametrize('value, type', INPUT)
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

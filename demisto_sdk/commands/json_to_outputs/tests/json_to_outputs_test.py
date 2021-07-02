import pytest
from demisto_sdk.commands.json_to_outputs.json_to_outputs import (
    determine_type, parse_json)


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
        prefix='Jira.Ticket'
    )

    assert yaml_output == '''arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.created_at
  description: ''
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
        data='[{"a": "b", "c": "d"}, {"e": "f"}]',
        command_name='jira-ticket',
        prefix='Jira.Ticket'
    )

    assert yaml_output == '''arguments: []
name: jira-ticket
outputs:
- contextPath: Jira.Ticket.a
  description: ''
  type: String
- contextPath: Jira.Ticket.c
  description: ''
  type: String
- contextPath: Jira.Ticket.e
  description: ''
  type: String
'''


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

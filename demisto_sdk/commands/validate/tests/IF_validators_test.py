from typing import List

import pytest

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.tests.test_tools import create_incident_field_object
from demisto_sdk.commands.validate.validators.IF_validators.IF100_is_valid_name_and_cli_name import (
    IsValidNameAndCliNameValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF101_is_valid_content_field import (
    IsValidContentFieldValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF102_is_valid_system_flag import (
    IsValidSystemFlagValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF103_is_valid_field_type import (
    FIELD_TYPES,
    IsValidFieldTypeValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_incident_field_object(["name", "cliName"], ["case 1", "case1"]),
                create_incident_field_object(["name", "cliName"], ["test 1", "test1"]),
            ],
            1,
            [
                (
                    "The words: [case] cannot be used as a name.\n"
                    "To fix the problem, remove the words [case], "
                    "or add them to the whitelist named argsExceptionsList in:\n"
                    "https://github.com/demisto/server/blob/57fbe417ae420c41ee12a9beb850ff4672209af8/services/servicemodule_test.go#L8273"
                )
            ],
        ),
        (
            [
                create_incident_field_object(
                    ["name", "cliName"], ["case incident 1", "caseincident1"]
                ),
            ],
            1,
            [
                (
                    "The words: [case, incident] cannot be used as a name.\n"
                    "To fix the problem, remove the words [case, incident], "
                    "or add them to the whitelist named argsExceptionsList in:\n"
                    "https://github.com/demisto/server/blob/57fbe417ae420c41ee12a9beb850ff4672209af8/services/servicemodule_test.go#L8273"
                )
            ],
        ),
    ],
)
def test_IsValidNameAndCliNameValidator_is_valid(
    content_items: List[IncidentField],
    expected_number_of_failures: int,
    expected_msgs: List[str],
):
    """
    Given:
        - IncidentFields content items
          Case 1:
            - IncidentField with bad word in field `name`
            - IncidentField with valid field `name`
          Case 2:
            - IncidentField with two bad words in field `name`
    When:
        - run is_valid method
    Then:
        Case 1:
            - Ensure the error message is as expected
            - Ensure number of failure is as expected
        Case 2:
            - Ensure the error message is as expected with the bad words list
    """
    results = IsValidNameAndCliNameValidator().is_valid(content_items=content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidContentFieldValidator_is_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'content' field is set to False
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["content"], [False]),
        create_incident_field_object(["content"], [True]),
    ]

    results = IsValidContentFieldValidator().is_valid(content_items)
    assert len(results) == 1
    assert all(
        [
            result.message == "The `content` key must be set to true"
            for result in results
        ]
    )


def test_IsValidContentFieldValidator_fix():
    """
    Given:
        - invalid IncidentField that its 'content' field is set to False
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `content` is set to true
    """
    incident_field = create_incident_field_object(["content"], [False])
    result = IsValidContentFieldValidator().fix(incident_field)
    assert result.message == "`content` field is set to true"
    assert incident_field.data["content"]


def test_IsValidSystemFlagValidator_is_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'system' field is set to True
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["system"], [True]),
        create_incident_field_object(["system"], [False]),
    ]

    results = IsValidSystemFlagValidator().is_valid(content_items)
    assert len(results) == 1
    assert all(
        [
            result.message == "The `system` key must be set to false"
            for result in results
        ]
    )


def test_IsValidSystemFlagValidator_fix():
    """
    Given:
        - invalid IncidentField that its 'system' field is set to True
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `system` is set to false
    """
    incident_field = create_incident_field_object(["system"], [True])
    result = IsValidSystemFlagValidator().fix(incident_field)
    assert result.message == "`system` field is set to false"
    assert not incident_field.data["system"]


def test_IsValidFieldTypeValidator_is_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'type' field is not valid
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["type"], ["test"]),
        create_incident_field_object(["type"], ["html"]),
    ]

    results = IsValidFieldTypeValidator().is_valid(content_items)
    assert len(results) == 1
    assert all(
        [
            result.message
            == f"Type: `test` is not one of available types.\navailable types: {FIELD_TYPES}"
            for result in results
        ]
    )

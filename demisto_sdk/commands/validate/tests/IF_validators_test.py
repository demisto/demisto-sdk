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
from demisto_sdk.commands.validate.validators.IF_validators.IF104_is_valid_group_field import (
    INCIDENT_FIELD_GROUP,
    IsValidGroupFieldValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF105_is_cli_name_field_alphanumeric import (
    IsCliNameFieldAlphanumericValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF106_is_cli_name_reserved_word import (
    IsCliNameReservedWordValidator,
)

""" NOT VALID """

@pytest.mark.parametrize(
    "content_items, expected_msgs",
    [
        pytest.param(
            [
                create_incident_field_object(["name", "cliName"], ["case 1", "case1"])
            ],
            [("The following words cannot be used as a name: case.")],
            id="One IncidentField with bad word in field `name`",
        ),
        pytest.param(
            [
                create_incident_field_object(
                    ["name", "cliName"], ["case incident 1", "caseincident1"]
                ),
            ],
            [("The following words cannot be used as a name: case, incident.")],
            id="IncidentField with two bad words in field `name`",
        ),
    ],
)
def test_IsValidNameAndCliNameValidator_not_valid(
    content_items: List[IncidentField],
    expected_msgs: List[str],
):
    """
    Given:
        - IncidentFields content items
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
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsValidContentFieldValidator_not_valid():
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
        create_incident_field_object(["content"], [False])
    ]

    results = IsValidContentFieldValidator().is_valid(content_items)
    assert all(
        [
            result.message == "The `content` key must be set to true."
            for result in results
        ]
    )


def test_IsValidSystemFlagValidator_not_valid():
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
        create_incident_field_object(["system"], [True])
    ]

    results = IsValidSystemFlagValidator().is_valid(content_items)
    assert all(
        [
            result.message == "The `system` key must be set to false."
            for result in results
        ]
    )


def test_IsValidFieldTypeValidator_not_valid():
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
        create_incident_field_object(["type"], ["test"])
    ]

    results = IsValidFieldTypeValidator().is_valid(content_items)
    assert all(
        [
            result.message
            == f"Type: `test` is not one of available types.\navailable types: {FIELD_TYPES}."
            for result in results
        ]
    )


def test_IsValidGroupFieldValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'group' field is not valid
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["group"], [2])
    ]

    results = IsValidGroupFieldValidator().is_valid(content_items)
    assert all([result.message == "Group 2 is not a group field." for result in results])


def test_IsCliNameFieldAlphanumericValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'cliName' value is non-alphanumeric
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], ["test_1234"])
    ]

    results = IsCliNameFieldAlphanumericValidator().is_valid(content_items)
    assert all(
        [
            result.message
            == "Field `cliName` contains non-alphanumeric or uppercase letters."
            for result in results
        ]
    )


def test_IsCliNameReservedWordValidator_not_valid():
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'cliName' value is a reserved word
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], ["parent"])
    ]

    results = IsCliNameReservedWordValidator().is_valid(content_items)
    assert len(results) == 1
    assert all(
        [
            result.message
            == "`cliName` field can not be `parent` as it's a builtin key."
            for result in results
        ]
    )


""" VALID """

def test_IsValidContentFieldValidator_valid():
    """
    Given:
        - IncidentField content items with a content value True
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["content"], [True])
    ]

    results = IsValidContentFieldValidator().is_valid(content_items)
    assert not results


def test_IsValidSystemFlagValidator_valid():
    """
    Given:
        - IncidentField content items with a system value False
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["system"], [False])
    ]

    results = IsValidSystemFlagValidator().is_valid(content_items)
    assert not results


def test_IsValidFieldTypeValidator_valid():
    """
    Given:
        - IncidentField content items with a valid type value
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["type"], ["html"])
    ]

    results = IsValidFieldTypeValidator().is_valid(content_items)
    assert not results

def test_IsValidGroupFieldValidator_valid():
    """
    Given:
        - IncidentField content items with a group value 0
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["group"], [0])
    ]

    results = IsValidGroupFieldValidator().is_valid(content_items)
    assert not results


def test_IsCliNameFieldAlphanumericValidator_valid():
    """
    Given:
        - IncidentField content items with a cliName value
          that is alphanumeric and lowercase letters
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], ["test1234"])
    ]

    results = IsCliNameFieldAlphanumericValidator().is_valid(content_items)
    assert not results


def test_IsCliNameReservedWordValidator_valid():
    """
    Given:
        - IncidentField content items with a cliName value that is not reserve word
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], ["test"])
    ]

    results = IsCliNameReservedWordValidator().is_valid(content_items)
    assert not results


""" FIX """

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
    assert result.message == "`content` field is set to true."
    assert incident_field.data["content"]


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
    assert result.message == "`system` field is set to false."
    assert not incident_field.data["system"]


def test_IsValidGroupFieldValidator_fix():
    """
    Given:
        - invalid IncidentField that 'group' field is not 0
    When:
        - run fix method
    Then:
        - Ensure the fix message as expected
        - Ensure the field `group` is set to 0
    """
    incident_field = create_incident_field_object(["group"], [1])
    result = IsValidGroupFieldValidator().fix(incident_field)
    assert result.message == f"`group` field is set to {INCIDENT_FIELD_GROUP}."
    assert incident_field.data["group"] == INCIDENT_FIELD_GROUP

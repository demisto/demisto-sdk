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
    REQUIRED_GROUP_VALUE,
    IsValidGroupFieldValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF105_is_cli_name_field_alphanumeric import (
    IsCliNameFieldAlphanumericValidator,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF106_is_cli_name_reserved_word import (
    INCIDENT_PROHIBITED_CLI_NAMES,
    IsCliNameReservedWordValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_msg",
    [
        pytest.param(
            create_incident_field_object(["name", "cliName"], ["case 1", "case1"]),
            "The following words cannot be used as a name: case.",
            id="One IncidentField with bad word in field `name`",
        ),
        pytest.param(
            create_incident_field_object(
                ["name", "cliName"], ["case incident 1", "caseincident1"]
            ),
            "The following words cannot be used as a name: case, incident.",
            id="IncidentField with two bad words in field `name`",
        ),
    ],
)
def test_IsValidNameAndCliNameValidator_not_valid(
    content_items: IncidentField,
    expected_msg: str,
):
    """
    Given:
        - IncidentFields content items
    When:
        - run is_valid method
    Then:
        Case 1:
            - Ensure the error message is as expected
        Case 2:
            - Ensure the error message is as expected with the bad words list
    """
    results = IsValidNameAndCliNameValidator().is_valid(content_items=[content_items])
    assert results
    assert results[0].message == expected_msg


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
    assert results
    assert results[0].message == "The `content` key must be set to true."


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
    assert results
    assert results[0].message == "The `system` key must be set to false."


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
    assert results
    assert (
        results[0].message
        == f"Type: `test` is not one of available types.\navailable types: {FIELD_TYPES}."
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
    content_items: List[IncidentField] = [create_incident_field_object(["group"], [2])]

    results = IsValidGroupFieldValidator().is_valid(content_items)
    assert results
    assert results[0].message == "The `group` key must be set to 0 for Incident Field"


@pytest.mark.parametrize("cli_name_value", ["", "Foo", "123_", "123A"])
def test_IsCliNameFieldAlphanumericValidator_not_valid(cli_name_value):
    """
    Given:
        - IncidentField content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'cliName' value is non-alphanumeric, or contains an uppercase letter.
    """
    content_items: List[IncidentField] = [
        create_incident_field_object(["cliName"], [cli_name_value])
    ]

    results = IsCliNameFieldAlphanumericValidator().is_valid(content_items)
    assert results
    assert (
        results[0].message
        == "Field `cliName` contains uppercase or non-alphanumeric symbols."
    )


@pytest.mark.parametrize("reserved_word", INCIDENT_PROHIBITED_CLI_NAMES)
def test_IsCliNameReservedWordValidator_not_valid(reserved_word):
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
        create_incident_field_object(["cliName"], [reserved_word])
    ]

    results = IsCliNameReservedWordValidator().is_valid(content_items)
    assert results
    assert (
        results[0].message
        == f"`cliName` field can not be `{reserved_word}` as it's a builtin key."
    )


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
    content_items: List[IncidentField] = [create_incident_field_object(["group"], [0])]

    results = IsValidGroupFieldValidator().is_valid(content_items)
    assert not results


@pytest.mark.parametrize("cli_name_value", ["foo1234", "foo", "1234"])
def test_IsCliNameFieldAlphanumericValidator_valid(cli_name_value):
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
        create_incident_field_object(["cliName"], [cli_name_value])
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
        create_incident_field_object(["cliName"], ["foo"])
    ]

    results = IsCliNameReservedWordValidator().is_valid(content_items)
    assert not results


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
    assert incident_field.content


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
    assert not incident_field.system


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
    assert result.message == f"`group` field is set to {REQUIRED_GROUP_VALUE}."
    assert incident_field.group == REQUIRED_GROUP_VALUE

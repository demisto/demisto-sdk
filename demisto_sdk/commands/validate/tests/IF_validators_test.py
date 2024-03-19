
import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_incident_field_object,
    create_old_file_pointers,
)
from demisto_sdk.commands.validate.validators.IF_validators.IF111_is_field_type_changed import (
    IsFieldTypeChangedValidator,
)


def test_IsFieldTypeChangedValidator_not_valid():
    """
    Given:
        - IncidentFiled content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the IncidentField whose 'type' field is changed
    """
    content_items = [
        create_incident_field_object(["type"], ["html"]),
    ]
    old_content_items = [
        create_incident_field_object(["type"], ["short text"])
    ]
    create_old_file_pointers(content_items, old_content_items)
    results = IsFieldTypeChangedValidator().is_valid(content_items)
    assert results
    assert results[0].message == "Changing incident field type is not allowed"


def test_IsFieldTypeChangedValidator_valid():
    """
    Given:
        - IncidentFiled whose type has not changed
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items = [
        create_incident_field_object(["type"], ["html"]),
    ]
    old_content_items = [
        create_incident_field_object(["type"], ["html"])
    ]
    create_old_file_pointers(content_items, old_content_items)
    results = IsFieldTypeChangedValidator().is_valid(content_items)
    assert not results

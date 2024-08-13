from demisto_sdk.commands.validate.tests.test_tools import create_incident_type_object
from demisto_sdk.commands.validate.validators.IT_validators.IT100_is_including_int_fields import (
    IncidentTypeIncludesIntFieldValidator,
)
from demisto_sdk.commands.validate.validators.IT_validators.IT101_is_valid_playbook_id import (
    IncidentTypValidPlaybookIdValidator,
)
from demisto_sdk.commands.validate.validators.IT_validators.IT102_is_auto_extract_fields_valid import (
    IncidentTypeValidAutoExtractFieldsValidator,
)
from demisto_sdk.commands.validate.validators.IT_validators.IT103_is_auto_extract_mode_valid import (
    IncidentTypeValidAutoExtractModeValidator,
)


def test_IncidentTypeIncludesIntFieldValidator_obtain_invalid_content_items():
    """
    Given:
        - Incident Type content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
          when all required fields has positive int values.
        - Ensure that the ValidationResult returned
          for the Incident Type who has a field with non integer value
    """
    incident_type = create_incident_type_object()

    # valid
    assert not IncidentTypeIncludesIntFieldValidator().obtain_invalid_content_items(
        [incident_type]
    )

    # not valid
    incident_type.data_dict["days"] = None
    incident_type.data_dict["daysR"] = "day"
    results = IncidentTypeIncludesIntFieldValidator().obtain_invalid_content_items(
        [incident_type]
    )
    assert (
        results[0].message
        == "The 'days, daysR' fields need to be included with a positive integer."
        " Please add them with positive integer value."
    )


def test_IncidentTypValidPlaybookIdValidator_obtain_invalid_content_items():
    """
    Given:
        - Incident Tyupe content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that the ValidationResult returned
          for the GenericField whose 'group' field is not valid
        - Ensure that no ValidationResult returned when group field set to 4
    """
    # valid
    incident_type = create_incident_type_object()
    assert not IncidentTypValidPlaybookIdValidator().obtain_invalid_content_items(
        [incident_type]
    )

    # not valid
    incident_type.playbook = "abbababb-aaaa-bbbb-cccc-abcdabcdabcd"
    results = IncidentTypValidPlaybookIdValidator().obtain_invalid_content_items(
        [incident_type]
    )
    assert (
        results[0].message
        == "The 'playbookId' field is not valid - please enter a non-UUID playbook ID."
    )


def test_IncidentTypeValidAutoExtractFieldsValidator_obtain_invalid_content_items():
    """
    Given:
        - Incident Type content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
          when all required fields has positive int values.
        - Ensure that the ValidationResult returned
          for the Incident Type who has a field with non integer value
    """
    incident_type = create_incident_type_object()

    # valid
    assert (
        not IncidentTypeValidAutoExtractFieldsValidator().obtain_invalid_content_items(
            [incident_type]
        )
    )

    # not valid
    incident_type.extract_settings = {
        "fieldCliNameToExtractSettings": {
            "incident field": {
                "isExtractingAllIndicatorTypes": True,
                "extractAsIsIndicatorTypeId": "doo",
                "extractIndicatorTypesIDs": "boo",
            }
        }
    }
    assert IncidentTypeValidAutoExtractFieldsValidator().obtain_invalid_content_items(
        [incident_type]
    )


def test_IncidentTypeValidAutoExtractModeValidator_obtain_invalid_content_items():
    """
    Given:
        - Incident Type content items
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
          when all required fields has positive int values.
        - Ensure that the ValidationResult returned
          for the Incident Type who has a field with non integer value
    """
    incident_type = create_incident_type_object()

    # valid
    assert not IncidentTypeValidAutoExtractModeValidator().obtain_invalid_content_items(
        [incident_type]
    )

    # not valid
    incident_type.extract_settings = {"mode": "foo"}
    assert IncidentTypeValidAutoExtractModeValidator().obtain_invalid_content_items(
        [incident_type]
    )

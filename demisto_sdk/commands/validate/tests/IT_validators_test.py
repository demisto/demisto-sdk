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


def test_IncidentTypeIncludesIntFieldValidator_is_valid():
    """
    Given:
        - Incident Type content items
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
          when all required fields has positive int values.
        - Ensure that the ValidationResult returned
          for the Incident Type who has a field with non integer value
    """
    incident_type = create_incident_type_object()

    # valid
    assert not IncidentTypeIncludesIntFieldValidator().is_valid([incident_type])

    # not valid
    incident_type.data["days"] = None
    incident_type.data["daysR"] = "day"
    results = IncidentTypeIncludesIntFieldValidator().is_valid([incident_type])
    assert (
        results[0].message
        == "The 'days, daysR' fields need to be included with a positive integer."
        " Please add them with positive integer value."
    )


def test_IncidentTypValidPlaybookIdValidator_is_valid():
    """
    Given:
        - Incident Tyupe content items
    When:
        - run is_valid method
    Then:
        - Ensure that the ValidationResult returned
          for the GenericField whose 'group' field is not valid
        - Ensure that no ValidationResult returned when group field set to 4
    """
    # valid
    incident_type = create_incident_type_object()
    assert not IncidentTypValidPlaybookIdValidator().is_valid([incident_type])

    # not valid
    incident_type.data["playbookId"] = "abbababb-aaaa-bbbb-cccc-abcdabcdabcd"
    results = IncidentTypValidPlaybookIdValidator().is_valid([incident_type])
    assert (
        results[0].message
        == "The 'playbookId' field is not valid - please enter a non-UUID playbook ID."
    )


def test_IncidentTypeValidAutoExtractFieldsValidator_is_valid():
    """
    Given:
        - Incident Type content items
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
          when all required fields has positive int values.
        - Ensure that the ValidationResult returned
          for the Incident Type who has a field with non integer value
    """
    incident_type = create_incident_type_object()

    # valid
    assert not IncidentTypeValidAutoExtractFieldsValidator().is_valid([incident_type])

    # not valid
    incident_type.data["extractSettings"] = {
        "fieldCliNameToExtractSettings": {
            "incident field": {
                "isExtractingAllIndicatorTypes": True,
                "extractAsIsIndicatorTypeId": "doo",
                "extractIndicatorTypesIDs": "boo",
            }
        }
    }
    assert IncidentTypeValidAutoExtractFieldsValidator().is_valid([incident_type])


def test_IncidentTypeValidAutoExtractModeValidato_is_valid():
    """
    Given:
        - Incident Type content items
    When:
        - run is_valid method
    Then:
        - Ensure that no ValidationResult returned
          when all required fields has positive int values.
        - Ensure that the ValidationResult returned
          for the Incident Type who has a field with non integer value
    """
    incident_type = create_incident_type_object()

    # valid
    assert not IncidentTypeValidAutoExtractFieldsValidator().is_valid([incident_type])

    # not valid
    incident_type.data["extractSettings"] = {"mode": "foo"}
    assert IncidentTypeValidAutoExtractFieldsValidator().is_valid([incident_type])

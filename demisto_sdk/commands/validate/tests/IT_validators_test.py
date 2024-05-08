from demisto_sdk.commands.validate.tests.test_tools import create_incident_type_object
from demisto_sdk.commands.validate.validators.IT_validators.IT100_is_including_int_fields import (
    IncidentTypeIncludesIntFieldValidator,
)
from demisto_sdk.commands.validate.validators.IT_validators.IT101_is_valid_playbook_id import (
    IncidentTypValidPlaybookIdValidator,
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


# @pytest.mark.parametrize("unsearchable", (False, None))
# def test_UnsearchableKeyValidator_is_valid(unsearchable: bool):
#     """
#     Given:
#         - GenericField content items
#     When:
#         - run is_valid method
#     Then:
#         - Ensure that the ValidationResult returned
#           for the GenericField whose 'unsearchable' field is set to false or not or undefined
#         - Ensure that no ValidationResult returned when unsearchable set to true
#     """
#     # not valid
#     generic_field = create_generic_field_object(
#         paths=["unsearchable"], values=[unsearchable]
#     )
#     assert UnsearchableKeyValidator().is_valid([generic_field])
#
#     # valid
#     generic_field.unsearchable = True
#     assert not UnsearchableKeyValidator().is_valid([generic_field])
#
#
# def test_GenericFieldGroupValidator_fix():
#     """
#     Given:
#         - invalid GenericField that 'group' field is not 4
#     When:
#         - run fix method
#     Then:
#         - Ensure the fix message as expected
#         - Ensure the field `group` is set to 4
#     """
#     generic_field = create_generic_field_object(paths=["group"], values=["0"])
#     result = GenericFieldGroupValidator().fix(generic_field)
#     assert result.message == f"set the `group` field to {REQUIRED_GROUP_VALUE}."
#     assert generic_field.group == REQUIRED_GROUP_VALUE

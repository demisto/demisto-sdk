import pytest
from demisto_sdk.commands.validate.validators.WZ_validators.WZ104_is_wrong_link_in_wizard import (
    IsWrongLinkInWizardValidator,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_wizard_object,
)


def test_IsWrongLinkInWizardValidator_valid_case():
    wizard = create_wizard_object()
    assert not IsWrongLinkInWizardValidator().is_valid([wizard])


def test_IsWrongLinkInWizardValidator_invalid_case():
    wizard = create_wizard_object(dict_to_update={'wizard': {'fetching_integrations': [], "set_playbook": [
        {"name": "Endpoint Malware Investigation - Generic V2", "link_to_integration": "CrowdstrikeFalcon"},
        {"name": "Endpoint_2 Malware Investigation - Generic V2",
         "link_to_integration": "Microsoft Defender Advanced Threat Protection"}], "supporting_integrations": [
        {"name": "WildFire-v2", "action": {"existing": "something", "new": "something else"},
         "description": "description"},
        {"name": "EWS Mail Sender", "action": {"existing": "something", "new": "something else"},
         "description": "description"}], "next": [
        {"name": "turn on use case", "action": {"existing": "something", "new": "something else"}}]}})
    results = IsWrongLinkInWizardValidator().is_valid([wizard])
    expected_error_messages = ['CrowdstrikeFalcon', 'Microsoft Defender Advanced Threat Protection']
    assert results
    integrations_without_playbook_from_error_message = results[0].message.split(': ')[1]
    result_error_messages = integrations_without_playbook_from_error_message.split(', ')
    for result_error_message, expected_error_message in zip(result_error_messages, expected_error_messages):
        assert result_error_message == expected_error_message

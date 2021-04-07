import pytest
import yaml
from demisto_sdk.commands.common.hook_validations.description import \
    DescriptionValidator


@pytest.mark.parametrize('integration_obj', [
    ({'script': {'script': 'Here Comes The Script'}}),
    ({'deprecated': True})
])
def test_is_duplicate_description_unified_deprecated_integration(mocker, tmp_path, integration_obj):
    """
    Given:
        - Case A: Content pack with unified integration
        - Case B: Content pack with deprecated integration

    When:
        - Running detailed description validator on the integration

    Then:
        - Ensure validation passes
        - Ensure no warning is printed
    """
    mocker.patch.object(DescriptionValidator, 'handle_error')
    integration_dir = tmp_path / 'Packs' / 'SomePack' / 'Integrations' / 'SomeIntegration'
    integration_dir.mkdir(parents=True)
    unified_integration_yml = integration_dir / 'SomeIntegration.yml'
    yaml.dump(integration_obj, unified_integration_yml.open('w'), default_flow_style=False)
    description_validator = DescriptionValidator(str(unified_integration_yml))
    assert description_validator.is_duplicate_description()
    assert not DescriptionValidator.handle_error.called


@pytest.mark.parametrize("file_input, result",
                         [("### Community Contributed Integration\n### OtherSection", False),
                          ("### partner Contributed Integration", False),
                          ("### Other section", True)])
def test_is_valid_file(integration, file_input, result):
    """
    Given
        - Description file with Contribution details or not
    When
        - Run validate on Description file
    Then
        - Ensure no Contribution details in the file
    """

    integration.description.write(file_input)
    description_path = integration.description.path
    description_validator = DescriptionValidator(description_path)
    answer = description_validator.is_valid_file()

    assert answer == result
    assert description_validator._is_valid == answer

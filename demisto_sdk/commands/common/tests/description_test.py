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

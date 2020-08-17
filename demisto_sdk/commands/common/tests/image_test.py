import os

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations import image
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.tests.integration_test import mock_structure


def test_is_not_default_image():
    int_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                             'integration-Zoom.yml'))
    image.INTEGRATION_REGXES.append(int_path)
    image_validator = image.ImageValidator(int_path)
    assert image_validator.is_not_default_image() is False

    image_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                               'default_image.png'))
    image.YML_INTEGRATION_REGEXES.append(image_path)
    image_validator = image.ImageValidator(image_path)
    assert image_validator.is_not_default_image() is False

    image_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/init/templates',
                                               'HelloWorld', 'HelloWorld_image.png'))
    image.YML_INTEGRATION_REGEXES.append(image_path)
    image_validator = image.ImageValidator(image_path)
    assert image_validator.is_not_default_image() is False

    int_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                             'fake_integration.yml'))
    image.INTEGRATION_REGXES.append(int_path)
    image_validator = image.ImageValidator(int_path)
    assert image_validator.is_not_default_image() is False


def test_is_valid_image_positive(monkeypatch):
    """
    Given
        - An integration is with a valid non default image

    When
        - Validating this integration

    Then
        - Ensure integration is considered valid
    """
    integration_path = os.path.normpath(
        os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files', 'not_default_image_integration-Zoom.yml')
    )
    structure = mock_structure(file_path=integration_path)
    monkeypatch.setattr('demisto_sdk.commands.common.hook_validations.image.INTEGRATION_REGXES', [integration_path])
    # Adding monkey patching this will make image validator behave like this is an integration outside of
    # pack context and ignore the image that's in the same folder as the file
    monkeypatch.setattr('demisto_sdk.commands.common.hook_validations.image.PACKS_INTEGRATION_NON_SPLIT_YML_REGEX',
                        integration_path)
    validator = IntegrationValidator(structure)
    assert validator.is_valid_image() is True


def test_image_in_both_yml_and_directory(monkeypatch):
    """
    Given
        - An integration that has image in both yml file and in the yml directory

    When
        - Validating this integration

    Then
        - Ensure integration is considered non-valid
    """
    integration_path = os.path.normpath(
        os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files', 'not_default_image_integration-Zoom.yml')
    )
    structure = mock_structure(file_path=integration_path)
    monkeypatch.setattr('demisto_sdk.commands.common.hook_validations.image.INTEGRATION_REGXES', [integration_path])
    validator = IntegrationValidator(structure)
    assert validator.is_valid_image() is False


def test_image_when_invalid_type(monkeypatch):
    """
    Given
        - An integration that has an invalid image

    When
        - Validating this integration

    Then
        - Ensure integration is considered non-valid.
    """
    integration_path = os.path.normpath(
        os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files', 'not_default_image_integration-Zoom.yml')
    )
    structure = mock_structure(file_path=integration_path)
    monkeypatch.setattr('demisto_sdk.commands.common.hook_validations.image.INTEGRATION_REGXES', [])
    validator = IntegrationValidator(structure)
    assert validator.is_valid_image() is False

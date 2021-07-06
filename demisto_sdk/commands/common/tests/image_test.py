import json
import os

from demisto_sdk.commands.common.hook_validations import image
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tests.integration_test import mock_structure
from TestSuite.file import File
from TestSuite.test_tools import ChangeCWD


def test_is_not_default_image():
    int_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                             'integration-Zoom.yml'))
    image_validator = image.ImageValidator(int_path)
    assert image_validator.is_not_default_image() is False

    image_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                               'default_image.png'))
    image_validator = image.ImageValidator(image_path)
    assert image_validator.is_not_default_image() is False

    image_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/init/templates',
                                               'HelloWorld', 'HelloWorld_image.png'))
    image_validator = image.ImageValidator(image_path)
    assert image_validator.is_not_default_image() is False

    int_path = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                             'fake_integration.yml'))
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
    validator = IntegrationValidator(structure)
    assert validator.is_valid_image() is False


def test_no_image_integration(monkeypatch):
    """
    Given
        - A new integration yml that does not have an image in its pack

    When
        - Validating this integration

    Then
        - Ensure integration is considered non-valid.
    """
    integration_path = os.path.normpath(
        os.path.join(f'{git_path()}/demisto_sdk/tests', 'test_files', 'DummyPack', 'Integrations',
                     'integration-DummyIntegration.yml')
    )
    structure = mock_structure(file_path=integration_path)
    validator = IntegrationValidator(structure)
    assert validator.is_valid_image() is False


def test_json_outputs_where_no_image_in_integration(repo):
    """
        Given
            - An integration without an existing image
            - A json file for writing the outputs

        When
            - Validating the image integration

        Then
            - Ensure that the outputs are correct.
    """
    # Create pack and integration
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('IntName')
    integration.create_default_integration()

    # Remove the integration image
    image_path = os.path.join(integration.path, 'IntName_image.png')
    if os.path.exists(image_path):
        os.remove(image_path)

    with ChangeCWD(repo.path):
        # Run the image validator with a json file path
        json_file_path = os.path.join(integration.path, 'json_outputs.json')
        image_validator = image.ImageValidator(integration.yml.path, json_file_path=json_file_path)

        # Check the outputs in the json file
        with open(image_validator.json_file_path, "r") as r:
            json_outputs = json.loads(r.read())

            assert json_outputs[0]['filePath'] == image_path
            assert json_outputs[0]['fileType'] == 'png'
            assert json_outputs[0]['entityType'] == 'image'


def test_is_valid_image_name_with_valid_name(repo):
    """
        Given
            - An integration image with a valid name

        When
            - Validating the integration image name

        Then
            - Ensure that image validator for integration passes.
    """

    pack = repo.create_pack('PackName')

    integration = pack.create_integration('IntName')
    integration.create_default_integration()

    image_validator = image.ImageValidator(integration.yml.path)

    assert image_validator.is_valid_image_name()


def test_is_valid_image_name_with_invalid_name(repo):
    """
        Given
            - An integration image with a invalid name

        When
            - Validating the integration image name

        Then
            - Ensure that image validator for integration failed.
    """

    pack = repo.create_pack('PackName')

    integration = pack.create_integration('IntName')
    integration.create_default_integration()

    if os.path.exists(integration.image.path):
        os.remove(integration.image.path)
        integration.image = None

    integration.image = File(integration._tmpdir_integration_path / f'{integration.name}_img.png',
                             integration._repo.path)

    with ChangeCWD(repo.path):

        image_validator = image.ImageValidator(integration.image.path)

        assert not image_validator.is_valid_image_name()

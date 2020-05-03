import os

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations import image


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

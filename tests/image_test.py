from demisto_sdk.common.hook_validations import image


def test_is_not_default_image():
    image.INTEGRATION_REGEX = 'test_files/integration-Zoom.yml'
    image_validator = image.ImageValidator('test_files/integration-Zoom.yml')
    assert image_validator.is_not_default_image() is True
    image.INTEGRATION_YML_REGEX = 'test_files/default_image.png'
    image_validator = image.ImageValidator("test_files/default_image.png")
    assert image_validator.is_not_default_image() is False
    image.INTEGRATION_REGEX = 'test_files/fake_integration.yml'
    image_validator = image.ImageValidator("test_files/fake_integration.yml")
    assert image_validator.is_not_default_image() is False

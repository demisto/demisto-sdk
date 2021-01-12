from demisto_sdk.commands.common.constants import DEFAULT_IMAGE_BASE64
from demisto_sdk.commands.common.content.objects.pack_objects.image.image import \
    Image

INVALID_IMAGE = "data:image/png;base32,iVBORw0KGgoAAAANSUhEUgAAAFAAAABTCAMAAAC5zwKfAAACYVBMVEVHcEwAT4UAT4UAT4YAf/8A"


def mock_integration(repo, default=True):
    pack = repo.create_pack('Temp')
    integration = pack.create_integration('MyIntegration')
    integration.create_default_integration()
    if default:
        integration.create_default_image()
    return integration


def test_is_not_default_image_invalid(repo):
    image = mock_integration(repo).image
    img_obj = Image(image.path)
    assert img_obj.is_not_default_image() is False


def test_is_not_default_image_invalid_integration(repo):
    integration = mock_integration(repo)
    img_obj = Image(integration.yml.path)
    assert img_obj.is_not_default_image() is False


def test_is_not_default_image_valid(repo):
    image = mock_integration(repo, default=False).image
    img_obj = Image(image.path)
    assert img_obj.is_not_default_image() is True


def test_is_not_default_image_valid_integration(repo):
    integration = mock_integration(repo, default=False)
    img_obj = Image(integration.yml.path)
    assert img_obj.is_not_default_image() is True


def test_is_valid_image_positive(repo):
    """
    Given
        - An integration is with a valid non default image

    When
        - Validating this integration

    Then
        - Ensure integration is considered valid
    """
    integration = mock_integration(repo, default=False)
    img_obj = Image(integration.yml.path)
    assert img_obj.is_valid_image() is True


def test_image_in_both_yml_and_directory(repo):
    """
    Given
        - An integration that has image in both yml file and in the yml directory

    When
        - Validating this integration

    Then
        - Ensure integration is considered non-valid
    """
    integration = mock_integration(repo, default=False)
    integration.yml.update({'image': DEFAULT_IMAGE_BASE64})
    img_obj = Image(integration.yml.path)
    assert img_obj.is_existing_image() is False


def test_image_when_invalid_type(repo):
    """
    Given
        - A unified integration that has an invalid image (in base32)

    When
        - Validating this integration

    Then
        - Ensure integration is considered non-valid.
    """
    integration = mock_integration(repo, default=False)
    # unified integration with invalid image
    integration.yml.update({'image': INVALID_IMAGE,
                            'script': {'script': 'some-code'}})
    img_obj = Image(integration.yml.path)
    assert img_obj.is_valid_image() is False


def test_no_image_integration(repo):
    """
    Given
        - A new integration yml that does not have an image in its pack

    When
        - Validating this integration

    Then
        - Ensure integration is considered non-valid.
    """
    integration = mock_integration(repo, default=False)
    # unified integration with no image
    integration.yml.update({'script': {'script': 'some-code'}})
    integration.yml.delete('image')
    img_obj = Image(integration.yml.path)
    assert img_obj.is_valid_image() is False

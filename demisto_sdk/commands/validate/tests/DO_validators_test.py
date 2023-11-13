import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO108_docker_image_exist import (
    DockerImageExistValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        (
            [
                create_integration_object(key_path="script.dockerimage", new_value=""),
                create_integration_object(),
            ],
            1,
        ),
        (
            [
                create_script_object(key_path="dockerimage", new_value=""),
                create_script_object(),
            ],
            1,
        ),
        (
            [
                create_script_object(),
                create_integration_object(),
            ],
            0,
        ),
        (
            [
                create_script_object(key_path="dockerimage", new_value=""),
                create_integration_object(key_path="script.dockerimage", new_value=""),
            ],
            2,
        ),
    ],
)
def test_DockerImageExistValidator_is_valid(content_items, expected_number_of_failures):
    """
    Given
    content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has no docker image and the second one does.
        - Case 2: content_items with 2 script where the first one has no docker image and the second one does.
        - Case 3: content_items with one script and one integration where both have docker image.
        - Case 4: content_items with one script and one integration where both have no docker image.
    When
    - Calling the DockerImageExistValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 integration.
        - Case 3: Should fail 0 integration.
        - Case 4: Should fail 2 integration.
    """
    assert (
        len(DockerImageExistValidator().is_valid(content_items))
        == expected_number_of_failures
    )

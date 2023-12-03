import pytest

from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO108_docker_image_exist import (
    DockerImageExistValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs, expected_call_count",
    [
        (
            [
                create_integration_object(paths=["script.dockerimage"], values=[""]),
                create_integration_object(),
            ],
            1,
            [
                "The Integration TestIntegration is missing a docker image, please make sure to add one.\n The recommended default docker is demisto/python3:3.1.1.1."
            ],
            1,
        ),
        (
            [
                create_script_object(
                    paths=["dockerimage", "subtype"], values=["", "python2"]
                ),
                create_script_object(),
            ],
            1,
            [
                "The Script myScript is missing a docker image, please make sure to add one.\n The recommended default docker is demisto/python2:3.1.1.1."
            ],
            1,
        ),
        (
            [
                create_script_object(),
                create_integration_object(),
            ],
            0,
            [],
            0,
        ),
        (
            [
                create_script_object(paths=["dockerimage"], values=[""]),
                create_integration_object(paths=["script.dockerimage"], values=[""]),
            ],
            2,
            [
                "The Script myScript is missing a docker image, please make sure to add one.\n The recommended default docker is demisto/python3:3.1.1.1.",
                "The Integration TestIntegration is missing a docker image, please make sure to add one.\n The recommended default docker is demisto/python3:3.1.1.1.",
            ],
            1,
        ),
    ],
)
def test_DockerImageExistValidator_is_valid(
    mocker,
    content_items,
    expected_number_of_failures,
    expected_msgs,
    expected_call_count,
):
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
        - Make sure the right amount of failures, and the correct msgs are returned, and also that the mocker wasn't called more than once.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 script.
        - Case 3: Should'nt fail at all.
        - Case 4: Should fail all content items.
    """
    mocker = mocker.patch.object(
        DockerImageValidator,
        "get_docker_image_latest_tag_request",
        return_value="3.1.1.1",
    )
    results = DockerImageExistValidator().is_valid(content_items)
    len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )
    mocker.call_count == expected_call_count

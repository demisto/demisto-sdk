import pytest

from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO101_docker_image_tag_is_not_latest import (
    LatestDockerImageTagValidator,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO102_docker_image_is_not_demisto import (
    DockerImageIsNotDemistoValidator,
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
            2,
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
        - Case 3: Shouldn't fail at all.
        - Case 4: Should fail all content items.
    """
    mocker = mocker.patch.object(
        DockerHubClient,
        "get_latest_docker_image_tag",
        return_value="3.1.1.1",
    )
    results = DockerImageExistValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    for result, expected_msg in zip(results, expected_msgs):
        assert result.message == expected_msg

    assert mocker.call_count == expected_call_count


def test_LatestDockerImageTagValidator_is_valid():
    """
    Given:
     - 1 integration and 1 script which uses the latest tag
     - 1 integration and 1 script which do not use the 'latest' tag
     - 1 integration and 1 script that are javascript

    When:
     - Running the DefaultDockerImageValidator validator

    Then:
     - make sure the integrations/scripts with the "latest" tags are not valid
    """
    content_items = [
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:latest"
            ],  # integration with 'latest' as the docker tag
        ),
        create_script_object(
            paths=["dockerimage"],
            values=["demisto/python3:latest"],  # script with 'latest' as the docker tag
        ),
        create_integration_object(),  # integration without 'latest' docker tag
        create_script_object(),  # script without 'latest' docker tag
        create_integration_object(
            paths=["script.type"], values=["javascript"]
        ),  # javascript integration
        create_script_object(
            paths=["type"], values=["javascript"]
        ),  # javascript script
    ]
    results = LatestDockerImageTagValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.docker_image == "demisto/python3:latest"


def test_DockerImageIsNotDemistoValidator_is_valid():
    """
    Given:
     - 1 integration and 1 script which uses a valid demisto version
     - 1 integration and 1 script which do not use a valid demisto version
     - 1 integration and 1 script that are javascript

    When:
     - Running the DefaultDockerImageValidator validator

    Then:
     - make sure the integrations/scripts that do not have valid demisto images are not valid
    """
    content_items = [
        create_integration_object(
            paths=["script.dockerimage"],
            values=["repository/python3:latest"],  # integration with non-demisto image
        ),
        create_script_object(
            paths=["dockerimage"],
            values=["repository/python3:latest"],  # script with non-demisto image
        ),
        create_integration_object(),  # integration with demisto image
        create_script_object(),  # script with demisto image
        create_integration_object(
            paths=["script.type"], values=["javascript"]
        ),  # javascript integration
        create_script_object(
            paths=["type"], values=["javascript"]
        ),  # javascript script
    ]
    results = DockerImageIsNotDemistoValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.docker_image == "repository/python3:latest"

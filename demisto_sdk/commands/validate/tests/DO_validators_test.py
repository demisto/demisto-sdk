import pytest
from requests.exceptions import HTTPError

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
from demisto_sdk.commands.validate.validators.DO_validators.DO106_docker_image_is_latest_tag import (
    DockerImageTagIsLatestNumericVersionValidator,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO107_docker_image_does_not_exist_in_dockerhub import (
    DockerImageDoesNotExistInDockerhubValidator,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO109_docker_image_is_not_deprecated import (
    DockerImageIsNotDeprecatedValidator,
)
from demisto_sdk.commands.validate.validators.DO_validators.DO110_docker_image_is_not_native_image import (
    DockerImageIsNotNativeImageValidator,
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
    results = DockerImageIsNotDeprecatedValidator().is_valid(content_items)
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
     - Running the LatestDockerImageTagValidator validator

    Then:
     - make sure the integrations/scripts with the "latest" tags are not valid
     - make sure that javascripts integrations/scripts are ignored
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
     - Running the DockerImageIsNotDemistoValidator validator

    Then:
     - make sure the integrations/scripts that are not valid demisto images fail
     - make sure that javascripts integrations/scripts are ignored
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


def test_DockerImageTagIsLatestNumericVersionValidator_is_valid(mocker, requests_mock):
    """
    Given:
     - 1 integration and 1 script which uses a valid demisto version but not with the latest tag
     - 1 integration and 1 script which uses a valid demisto version with the latest tag
     - 1 integration and 1 script that are javascript

    When:
     - Running the DockerImageTagIsLatestNumericVersionValidator validator

    Then:
     - make sure the integrations/scripts that do not have the latest tag are not valid
     - make sure that javascripts integrations/scripts are ignored
    """
    content_items = [
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.78623"
            ],  # integration with demisto image that is not the latest tag
        ),
        create_script_object(
            paths=["dockerimage"],
            values=[
                "demisto/ml:1.0.0.32340"
            ],  # script with demisto image that is not the latest tag
        ),
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.79623"
            ],  # integration with demisto image that is the latest tag
        ),
        create_script_object(
            paths=["dockerimage"],
            values=[
                "demisto/ml:1.0.0.33340"
            ],  # script with demisto image that is the latest tag
        ),
        create_integration_object(
            paths=["script.type"], values=["javascript"]
        ),  # javascript integration
        create_script_object(
            paths=["type"], values=["javascript"]
        ),  # javascript script
    ]

    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "1234", "issued_at": "1234", "expires_in": 300},
    )
    requests_mock.get(
        f"{DockerHubClient.DEFAULT_REGISTRY}/demisto/python3/tags/list",
        json={"tags": ["3.10.13.78623", "3.10.13.79623"]},
    )
    requests_mock.get(
        f"{DockerHubClient.DEFAULT_REGISTRY}/demisto/ml/tags/list",
        json={"tags": ["1.0.0.32340", "1.0.0.33340"]},
    )
    mocker.patch.object(
        DockerImageTagIsLatestNumericVersionValidator,
        "is_docker_image_older_than_three_days",
        return_value=True,
    )

    results = DockerImageTagIsLatestNumericVersionValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.docker_image in (
            "demisto/python3:3.10.13.78623",
            "demisto/ml:1.0.0.32340",
        )


def test_DockerImageDoesNotExistInDockerhubValidator_is_valid(requests_mock):
    """
    Given:
     - 1 integration and 1 script which uses a valid demisto image that exists in dockerhub
     - 1 integration and 1 script which uses a demisto image that does not exist in dockerhub
     - 1 integration and 1 script that are javascript

    When:
     - Running the DockerImageDoesNotExistInDockerhubValidator validator

    Then:
     - make sure the integrations/scripts that do not exist in dockerhub are not valid
     - make sure that javascripts integrations/scripts are ignored
    """
    content_items = [
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.55555"
            ],  # integration with demisto image that does not exist
        ),
        create_script_object(
            paths=["dockerimage"],
            values=[
                "demisto/ml:1.0.0.32342"
            ],  # script with demisto image that does not exist
        ),
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.79623"
            ],  # integration with demisto image that exists
        ),
        create_script_object(
            paths=["dockerimage"],
            values=["demisto/ml:1.0.0.33340"],  # script with demisto image that exists
        ),
        create_integration_object(
            paths=["script.type"], values=["javascript"]
        ),  # javascript integration
        create_script_object(
            paths=["type"], values=["javascript"]
        ),  # javascript script
    ]

    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "1234", "issued_at": "1234", "expires_in": 300},
    )
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/python3/tags/3.10.13.79623",
        json={"tags": ["3.10.13.78623", "3.10.13.79623"]},
    )
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/ml/tags/1.0.0.33340",
        json={"tags": ["1.0.0.32340", "1.0.0.33340"]},
    )
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/python3/tags/3.10.13.55555",
        exc=HTTPError("error"),
    )
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/ml/tags/1.0.0.32342",
        exc=HTTPError("error"),
    )

    results = DockerImageDoesNotExistInDockerhubValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.docker_image in (
            "demisto/python3:3.10.13.55555",
            "demisto/ml:1.0.0.32342",
        )


def test_DockerImageIsNotDeprecatedValidator_is_valid(mocker, requests_mock):
    """
    Given:
     - 1 integration and 1 script which uses a deprecated docker image
     - 1 integration and 1 script which do not use a deprecated docker image
     - 1 integration and 1 script that are javascript

    When:
     - Running the DockerImageDoesNotExistInDockerhubValidator validator

    Then:
     - make sure the integrations/scripts that use deprecated docker images are not valid
     - make sure that javascripts integrations/scripts are ignored
    """
    from demisto_sdk.commands.common.git_content_config import GitContentConfig

    mocker.patch.object(
        GitContentConfig,
        "_search_github_repo",
        return_value=("githubusercontent.com", "demisto/dockerfiles"),
    )

    requests_mock.get(
        "https://raw.githubusercontent.com/demisto/dockerfiles/master/docker/deprecated_images.json",
        json=[
            {
                "image_name": "demisto/aiohttp",
                "reason": "Use the demisto/py3-tools docker image instead.",
                "created_time_utc": "2022-05-31T17:51:17.226278Z",
            },
            {
                "image_name": "demisto/algorithmia",
                "reason": "Use the demisto/py3-tools docker image instead.",
                "created_time_utc": "2022-05-31T17:51:30.043632Z",
            },
        ],
    )

    content_items = [
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/aiohttp:3.10.13.55555"
            ],  # integration with demisto image that does not exist
        ),
        create_script_object(
            paths=["dockerimage"],
            values=[
                "demisto/algorithmia:1.0.0.32342"
            ],  # script with demisto image that does not exist
        ),
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.79623"
            ],  # integration with demisto image that exists
        ),
        create_script_object(
            paths=["dockerimage"],
            values=["demisto/ml:1.0.0.33340"],  # script with demisto image that exists
        ),
        create_integration_object(
            paths=["script.type"], values=["javascript"]
        ),  # javascript integration
        create_script_object(
            paths=["type"], values=["javascript"]
        ),  # javascript script
    ]

    results = DockerImageIsNotDeprecatedValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.docker_image in (
            "demisto/aiohttp:3.10.13.55555",
            "demisto/algorithmia:1.0.0.32342",
        )
    assert DockerImageIsNotDeprecatedValidator.deprecated_dockers_to_reasons


def test_DockerImageIsNotNativeImageValidator_is_valid():
    """
    Given:
     - 1 integration and 1 script which uses a native-image
     - 1 integration and 1 script which do not a native-image
     - 1 integration and 1 script that are javascript

    When:
     - Running the DockerImageIsNotNativeImageValidator validator

    Then:
     - make sure the integrations/scripts with the demisto/py3-native are not valid
     - make sure that javascripts integrations/scripts are ignored
    """
    content_items = [
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/py3-native"
            ],  # integration with native image configured as its docker image
        ),
        create_script_object(
            paths=["dockerimage"],
            values=[
                "demisto/py3-native"
            ],  # script with native image configured as its docker image
        ),
        create_integration_object(),  # integration without native image configured
        create_script_object(),  # script without native image configured
        create_integration_object(
            paths=["script.type"], values=["javascript"]
        ),  # javascript integration
        create_script_object(
            paths=["type"], values=["javascript"]
        ),  # javascript script
    ]
    results = DockerImageIsNotNativeImageValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.docker_image == "demisto/py3-native"

import pytest
import requests

from demisto_sdk.commands.common.docker.dockerhub_client import (
    DockerHubClient,
    DockerHubRequestException,
)
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)


@pytest.fixture(autouse=True)
def dockerhub_client() -> DockerHubClient:
    dockerhub_client = DockerHubClient(username="test", password="test")
    dockerhub_client.do_registry_get_request.cache_clear()
    dockerhub_client.do_docker_hub_get_request.cache_clear()
    return dockerhub_client


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_call_count",
    [
        (
            [
                create_integration_object(paths=["script.dockerimage"], values=[""]),
                create_integration_object(),
            ],
            1,
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
            1,
        ),
        (
            [
                create_script_object(),
                create_integration_object(),
            ],
            0,
            0,
        ),
        (
            [
                create_script_object(paths=["dockerimage"], values=[""]),
                create_integration_object(paths=["script.dockerimage"], values=[""]),
            ],
            2,
            2,
        ),
    ],
)
def test_DockerImageExistValidator_is_valid(
    mocker,
    content_items,
    expected_number_of_failures,
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
    from demisto_sdk.commands.validate.validators.DO_validators.DO104_docker_image_does_not_exist_in_yml import (
        DockerImageExistValidator,
    )

    _mocker = mocker.patch.object(
        DockerImageExistValidator, "get_latest_image", return_value="1.0.0"
    )

    results = DockerImageExistValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert _mocker.call_count == expected_call_count


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
    from demisto_sdk.commands.validate.validators.DO_validators.DO100_docker_image_tag_is_not_latest import (
        LatestDockerImageTagValidator,
    )

    content_items = [
        create_integration_object(
            paths=["name", "script.dockerimage"],
            values=[
                "LatestDockerImageIntegrationScript",
                "demisto/python3:latest",
            ],  # integration with 'latest' as the docker tag
        ),
        create_script_object(
            paths=["name", "dockerimage"],
            values=[
                "LatestDockerImageIntegrationScript",
                "demisto/python3:latest",
            ],  # script with 'latest' as the docker tag
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
        assert content_item.name == "LatestDockerImageIntegrationScript"


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
    from demisto_sdk.commands.validate.validators.DO_validators.DO101_docker_image_is_not_demisto import (
        DockerImageIsNotDemistoValidator,
    )

    content_items = [
        create_integration_object(
            paths=["name", "script.dockerimage"],
            values=[
                "NonDemistoImageIntegrationScript",
                "repository/python3:latest",
            ],  # integration with non-demisto image
        ),
        create_script_object(
            paths=["name", "dockerimage"],
            values=[
                "NonDemistoImageIntegrationScript",
                "repository/python3:latest",
            ],  # script with non-demisto image
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
        assert content_item.name == "NonDemistoImageIntegrationScript"


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
    from demisto_sdk.commands.validate.validators.DO_validators.DO106_docker_image_is_latest_tag import (
        DockerImageTagIsNotOutdated,
    )

    content_items = [
        create_integration_object(
            paths=["name", "script.dockerimage"],
            values=[
                "NotLatestTagIntegrationScript",
                "demisto/python3:3.10.13.11111",
            ],  # integration with demisto image that is not the latest tag
        ),
        create_script_object(
            paths=["name", "dockerimage"],
            values=[
                "NotLatestTagIntegrationScript",
                "demisto/ml:1.0.0.11111",
            ],  # script with demisto image that is not the latest tag
        ),
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.99999"
            ],  # integration with demisto image that is the latest tag
        ),
        create_script_object(
            paths=["dockerimage"],
            values=[
                "demisto/ml:1.0.0.99999"
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
        json={"tags": ["3.10.13.11111", "3.10.13.99999"]},
    )
    requests_mock.get(
        f"{DockerHubClient.DEFAULT_REGISTRY}/demisto/ml/tags/list",
        json={"tags": ["1.0.0.11111", "1.0.0.99999"]},
    )
    mocker.patch.object(
        DockerImageTagIsNotOutdated,
        "is_docker_image_older_than_three_months",
        return_value=True,
    )

    results = DockerImageTagIsNotOutdated().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.name == "NotLatestTagIntegrationScript"


def test_DockerImageTagIsLatestNumericVersionValidator_fix(requests_mock):
    """
    Given:
     - an integration that is not with the latest docker-image tag

    When:
     - Running the DockerImageTagIsLatestNumericVersionValidator fix

    Then:
     - make sure docker-image is getting updated to the latest docker tag
    """
    from demisto_sdk.commands.validate.validators.DO_validators.DO106_docker_image_is_latest_tag import (
        DockerImageTagIsNotOutdated,
    )

    integration = create_integration_object(
        paths=["script.dockerimage"],
        values=[
            "demisto/python3:3.10.13.55555",
        ],  # integration with demisto image that is not the latest tag
    )

    assert integration.docker_image == "demisto/python3:3.10.13.55555"

    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "1234", "issued_at": "1234", "expires_in": 300},
    )
    requests_mock.get(
        f"{DockerHubClient.DEFAULT_REGISTRY}/demisto/python3/tags/list",
        json={"tags": ["3.10.13.88888", "3.10.13.99999"]},
    )

    fix_result = DockerImageTagIsNotOutdated().fix(integration)
    assert fix_result.content_object.docker_image == "demisto/python3:3.10.13.99999"


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
    from demisto_sdk.commands.validate.validators.DO_validators.DO103_docker_image_does_not_exist_in_dockerhub import (
        DockerImageDoesNotExistInDockerhubValidator,
    )

    content_items = [
        create_integration_object(
            paths=["name", "script.dockerimage"],
            values=[
                "NonExistentDockerImageIntegrationScript",
                "demisto/python3:3.10.13.11111",
            ],  # integration with demisto image that does not exist
        ),
        create_script_object(
            paths=["name", "dockerimage"],
            values=[
                "NonExistentDockerImageIntegrationScript",
                "demisto/ml:1.0.0.11111",
            ],  # script with demisto image that does not exist
        ),
        create_integration_object(
            paths=["script.dockerimage"],
            values=[
                "demisto/python3:3.10.13.99999"
            ],  # integration with demisto image that exists
        ),
        create_script_object(
            paths=["dockerimage"],
            values=["demisto/ml:1.0.0.99999"],  # script with demisto image that exists
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
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/python3/tags/3.10.13.99999",
        json={"success": True},
    )
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/ml/tags/1.0.0.99999",
        json={"success": True},
    )
    response = requests.Response()
    response.status_code = 404
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/python3/tags/3.10.13.11111",
        exc=DockerHubRequestException(
            "error",
            exception=requests.RequestException(response=response),
        ),
    )
    requests_mock.get(
        f"{DockerHubClient.DOCKER_HUB_API_BASE_URL}/repositories/demisto/ml/tags/1.0.0.11111",
        exc=DockerHubRequestException(
            "error",
            exception=requests.RequestException(response=response),
        ),
    )

    results = DockerImageDoesNotExistInDockerhubValidator().is_valid(content_items)
    assert len(results) == 2
    for result in results:
        content_item: IntegrationScript = result.content_object
        assert content_item.type == "python"
        assert content_item.name == "NonExistentDockerImageIntegrationScript"


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
    from demisto_sdk.commands.validate.validators.DO_validators.DO105_docker_image_is_not_deprecated import (
        DockerImageIsNotDeprecatedValidator,
    )

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
            paths=["name", "script.dockerimage"],
            values=[
                "DeprecatedDockerImageIntegrationScript",
                "demisto/aiohttp:3.10.13.55555",
            ],  # integration with demisto image that is deprecated
        ),
        create_script_object(
            paths=["name", "dockerimage"],
            values=[
                "DeprecatedDockerImageIntegrationScript",
                "demisto/algorithmia:1.0.0.32342",
            ],  # script with demisto image that is deprecated
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
        assert content_item.name == "DeprecatedDockerImageIntegrationScript"

    # validate that the mapping between to deprecated dockers to their reasons is filled up
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
    from demisto_sdk.commands.validate.validators.DO_validators.DO102_docker_image_is_not_native_image import (
        DockerImageIsNotNativeImageValidator,
    )

    content_items = [
        create_integration_object(
            paths=["name", "script.dockerimage"],
            values=[
                "NativeImageDockerIntegrationScript",
                "demisto/py3-native",
            ],  # integration with native image configured as its docker image
        ),
        create_script_object(
            paths=["name", "dockerimage"],
            values=[
                "NativeImageDockerIntegrationScript",
                "demisto/py3-native",
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
        assert content_item.name == "NativeImageDockerIntegrationScript"

from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytest
from freezegun import freeze_time
from packaging.version import Version
from requests import Response, Session

from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json


@pytest.fixture()
def dockerhub_client() -> DockerHubClient:
    dockerhub_client = DockerHubClient(username="test", password="test")
    dockerhub_client.do_registry_get_request.cache_clear()
    dockerhub_client.do_docker_hub_get_request.cache_clear()
    return dockerhub_client


def test_get_token_with_new_token(requests_mock, dockerhub_client: DockerHubClient):
    """
    Given:
        - token from the api

    When:
        - running get_token method

    Then:
        - ensure that the token is extracted properly
        - ensure that the token is saved in the cache
    """
    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "1234", "issued_at": "1234", "expires_in": 300},
    )
    assert dockerhub_client.get_token(repo="test") == "1234"
    assert dockerhub_client._docker_hub_auth_tokens["test:pull"]
    assert dockerhub_client._docker_hub_auth_tokens["test:pull"] == {
        "token": "1234",
        "issued_at": "1234",
        "expires_in_seconds": 300,
    }


@freeze_time("2024-01-01 12:00:00")
def test_get_token_with_existing_not_expired_token(
    requests_mock, dockerhub_client: DockerHubClient
):
    """
    Given:
        - existing token from the cache that is not expired

    When:
        - running get_token method

    Then:
        - ensure that the token is extracted properly only from the cache without api-request
    """
    dockerhub_client._docker_hub_auth_tokens = {
        "test:pull": {
            "token": "1234",
            "issued_at": (datetime.now() - timedelta(minutes=8)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "expires_in_seconds": 300,
        }
    }
    requests_mock.get("https://auth.docker.io/token")
    assert dockerhub_client.get_token(repo="test") == "1234"
    assert not requests_mock.called


@freeze_time("2024-01-01 12:00:00")
def test_get_token_with_existing_expired_token(
    requests_mock, dockerhub_client: DockerHubClient
):
    """
    Given:
        - existing token from the cache that is expired

    When:
        - running get_token method

    Then:
        - ensure that the token is extracted from the api-request because token has expired
        - ensure the api is called
        - ensure that cache gets updated with the newly created token
    """
    dockerhub_client._docker_hub_auth_tokens = {
        "test:pull": {
            "token": "token_from_cache",
            "issued_at": (datetime.now() - timedelta(minutes=1)).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "expires_in_seconds": 300,
        }
    }
    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "token_from_api", "issued_at": "1234", "expires_in": 300},
    )
    assert dockerhub_client.get_token(repo="test") == "token_from_api"
    assert requests_mock.called
    assert dockerhub_client._docker_hub_auth_tokens["test:pull"] == {
        "token": "token_from_api",
        "issued_at": "1234",
        "expires_in_seconds": 300,
    }


@pytest.mark.parametrize(
    "tags, expected_highest_tag",
    [
        (
            [
                "3.10.13.78960",
                "3.10.13.81631",
                "3.10.12.68300",
                "3.10.11.61265",
                "3.8.3.9324",
                "3.9.8.24399",
            ],
            "3.10.13.81631",
        ),
        (["1.0.0.81877", "1.0.0.78900", "1.0.0.72295"], "1.0.0.81877"),
        (["1.0.0.81877", "1.0.0.78900", "2.0.0.72295"], "2.0.0.72295"),
        (
            [
                "invalid_value",
                "7.4.0.80528",
                "1.5.0.80528",
                "2.5.0.80528",
                "2.5.0.80529",
            ],
            "7.4.0.80528",
        ),
    ],
)
def test_get_latest_docker_image_tag(
    requests_mock,
    dockerhub_client: DockerHubClient,
    tags: List[str],
    expected_highest_tag: str,
):
    """
    Given:
        - lists of tags

    When:
        - running get_latest_docker_image_tag method

    Then:
        - ensure that the latest tag is returned always
    """
    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "1234", "issued_at": "1234", "expires_in": 300},
    )
    docker_image = "demisto/python3"
    requests_mock.get(
        f"{dockerhub_client.DEFAULT_REGISTRY}/{docker_image}/tags/list",
        json={"tags": tags},
    )
    assert dockerhub_client.get_latest_docker_image_tag(docker_image) == Version(
        expected_highest_tag
    )


@pytest.mark.parametrize(
    "responses, count",
    [
        (
            [
                {"count": 100, "results": list(range(30)), "next": "next_link"},
                {"count": 100, "results": list(range(30)), "next": "next_link"},
                {"count": 100, "results": list(range(30)), "next": "next_link"},
                {"count": 100, "results": list(range(10)), "next": None},
            ],
            100,
        ),
        (
            [
                {"count": 600, "results": list(range(100)), "next": "next_link"},
                {"count": 600, "results": list(range(100)), "next": "next_link"},
                {"count": 600, "results": list(range(100)), "next": "next_link"},
                {"count": 600, "results": list(range(100)), "next": "next_link"},
                {"count": 600, "results": list(range(100)), "next": "next_link"},
                {"count": 600, "results": list(range(100)), "next": None},
            ],
            600,
        ),
        (
            [
                {"count": 158, "results": list(range(100)), "next": "next_link"},
                {"count": 158, "results": list(range(58)), "next": None},
            ],
            158,
        ),
    ],
)
def test_do_docker_hub_get_request_with_pagination(
    mocker,
    dockerhub_client: DockerHubClient,
    responses: List[Dict[str, Any]],
    count: int,
):
    """
    Given:
        - pagination responses

    When:
        - running do_docker_hub_get_request method

    Then:
        - ensure that we retrieve all the objects eventually after pagination
    """
    mocked_responses = []
    for paged_response in responses:
        response = Response()
        response._content = json.dumps(paged_response).encode("utf-8")
        mocked_responses.append(response)

    mocker.patch.object(Session, "get", side_effect=mocked_responses)
    mocker.patch.object(Response, "raise_for_status")
    assert len(dockerhub_client.do_docker_hub_get_request(url_suffix="/test")) == count


def test_do_docker_hub_get_request_single_object(
    requests_mock, dockerhub_client: DockerHubClient
):
    """
    Given:
        - single object response

    When:
        - running do_docker_hub_get_request method

    Then:
        - ensure that we retrieve only the single object without pagination
    """
    response = Response()
    response._content = json.dumps({"test": "test"}).encode("utf-8")

    requests_mock.get(
        f"{dockerhub_client.DOCKER_HUB_API_BASE_URL}/test",
        json={"test": "test"},
    )

    assert dockerhub_client.do_docker_hub_get_request("/test") == {"test": "test"}

from datetime import datetime, timedelta
from typing import List

import pytest
from freezegun import freeze_time
from packaging.version import Version

from demisto_sdk.commands.common.docker.dockerhub_client import DockerHubClient


@pytest.fixture()
def dockerhub_client() -> DockerHubClient:
    return DockerHubClient(username="test", password="test")


def test_get_token_with_new_token(requests_mock, dockerhub_client: DockerHubClient):
    requests_mock.get(
        "https://auth.docker.io/token",
        json={"token": "1234", "issued_at": "1234", "expires_in": 300},
    )
    assert dockerhub_client.get_token(repo="test") == "1234"


@freeze_time("2024-01-01 12:00:00")
def test_get_token_with_existing_not_expired_token(
    requests_mock, dockerhub_client: DockerHubClient
):
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


def test_get_token_with_existing_expired_token(
    requests_mock, dockerhub_client: DockerHubClient
):
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

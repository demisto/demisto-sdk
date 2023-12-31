from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from demisto_sdk.commands.common.docker.dockerhub_api import DockerHubClient


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

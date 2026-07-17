from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlparse

import pytest
from freezegun import freeze_time
from packaging.version import Version
from requests import Response, Session

from demisto_sdk.commands.common.docker.dockerhub_client import (
    DockerHubClient,
    get_registry_api_url,
    iso8601_to_datetime_str,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json

_DOCKERHUB_CLIENT_MODULE = "demisto_sdk.commands.common.docker.dockerhub_client"


@pytest.fixture()
def dockerhub_client() -> DockerHubClient:
    dockerhub_client = DockerHubClient(username="test", password="test")
    dockerhub_client.do_registry_get_request.cache_clear()
    dockerhub_client.do_docker_hub_get_request.cache_clear()
    dockerhub_client._docker_hub_auth_tokens = {}
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


def test_get_token_ratelimit_with_username_password(
    mocker, dockerhub_client: DockerHubClient
):
    """
    Given:
        - no token from at the cache
        - rate-limit error with username/password
        - successful response without username/password

    When:
        - running get_token method

    Then:
        - ensure that the token is returned successfully
    """
    rate_limit_response = Response()
    rate_limit_response.status_code = 429
    rate_limit_response._content = b""
    valid_response = Response()
    valid_response.status_code = 200
    valid_response._content = json.dumps(
        {"token": "token_from_api", "issued_at": "1234", "expires_in": 300}
    ).encode("utf-8")
    mocker.patch.object(
        Session, "get", side_effect=[rate_limit_response, valid_response]
    )
    assert dockerhub_client.get_token(repo="test") == "token_from_api"


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
        (["1.0.0.61877", "1.0.0.78900", "2.0.0.79295"], "2.0.0.79295"),
        (["2.0.0.81877", "2.0.0.78900", "1.0.0.99295"], "1.0.0.99295"),
        (
            ["0.110.3.93571", "1.0.0.93128"],
            "0.110.3.93571",
        ),  # Important example of fastapi docker image.
        (
            [
                "invalid_value",
                "7.4.0.80530",
                "1.5.0.80528",
                "2.5.0.80528",
                "2.5.0.80529",
            ],
            "7.4.0.80530",
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
        - ensure that the latest tag is always returned. (decided by the build number showing up in the last place of
         the version tag e.g. 1.2.3.45 --> 45)

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


@pytest.mark.parametrize(
    "datetime_str, response",
    [
        ("2024-11-19T12:41:58.591749197Z", "2024-11-19T12:41:58.591749Z"),
        ("2024-11-19T12:41:58.591749Z", "2024-11-19T12:41:58.591749Z"),
        ("2024-11-19T12:41:58Z", "2024-11-19T12:41:58Z"),
        ("2024-11-19T12:41:58", "2024-11-19T12:41:58"),
    ],
)
def test_iso8601_to_datetime_str(datetime_str, response):
    """
    Given:
        - Datetime string with nanoseconds
    When:
        - Fetching datetime string from docker image response
    Then:
        - Ensure the datetime string is normalized converted to microseconds
    """
    assert iso8601_to_datetime_str(datetime_str) == response


DEFAULT_REGISTRY = "https://registry-1.docker.io/v2"


@pytest.mark.parametrize(
    "registry, expected_url",
    [
        pytest.param(
            "test-docker.dev",
            "https://test-docker.dev/v2",
            id="custom registry without scheme",
        ),
        pytest.param(
            "localhost:5050",
            "https://localhost:5050/v2",
            id="scheme-less host:port gets https prepended",
        ),
        pytest.param(
            "my-registry.example.com:8443",
            "https://my-registry.example.com:8443/v2",
            id="scheme-less host:port with hostname gets https prepended",
        ),
        pytest.param(
            "http://localhost:5050",
            "http://localhost:5050/v2",
            id="http host:port keeps http scheme",
        ),
        pytest.param(
            "http://localhost:5050/v2/",
            "http://localhost:5050/v2",
            id="http host:port with v2 trailing slash",
        ),
        pytest.param(
            "https://test-docker.dev",
            "https://test-docker.dev/v2",
            id="custom registry with https no v2",
        ),
        pytest.param(
            "https://test-docker.dev/v2",
            "https://test-docker.dev/v2",
            id="custom registry with https and v2",
        ),
        pytest.param(
            "https://test-docker.dev/",
            "https://test-docker.dev/v2",
            id="custom registry with trailing slash",
        ),
        pytest.param(
            "https://test-docker.dev/v2/",
            "https://test-docker.dev/v2",
            id="custom registry with v2 trailing slash",
        ),
        pytest.param(
            "http://my-registry.example.com",
            "http://my-registry.example.com/v2",
            id="custom registry with http scheme",
        ),
        pytest.param(
            "",
            DEFAULT_REGISTRY,
            id="empty registry returns default",
        ),
        pytest.param(
            "docker.io",
            DEFAULT_REGISTRY,
            id="default docker io returns default registry",
        ),
    ],
)
def test_get_registry_api_url_with_custom_registry(registry: str, expected_url: str):
    """
    Given:
        - Various custom registry URL formats

    When:
        - running get_registry_api_url to determine the registry API URL

    Then:
        - ensure the returned URL always has a scheme (https://) and the /v2 API path prefix
    """
    assert get_registry_api_url(registry, DEFAULT_REGISTRY) == expected_url


def test_get_registry_api_url_with_none_like_empty_registry():
    """
    Given:
        - An empty string registry (falsy value)

    When:
        - running get_registry_api_url

    Then:
        - ensure the default registry is returned
    """
    assert get_registry_api_url("", DEFAULT_REGISTRY) == DEFAULT_REGISTRY


def test_do_registry_get_request_custom_registry_skips_bearer_token(
    mocker, dockerhub_client: DockerHubClient
):
    """
    Given:
        - A DockerHubClient configured with a user-provided custom (non-Docker Hub) registry
          (e.g., JFrog), where _is_custom_registry is True

    When:
        - running do_registry_get_request

    Then:
        - ensure get_token is NOT called (no Docker Hub bearer token)
        - ensure the request is made with Accept header but without Authorization header
    """
    dockerhub_client.registry_api_url = "https://test-docker.dev/v2"
    dockerhub_client._is_custom_registry = True
    mock_get_token = mocker.patch.object(dockerhub_client, "get_token")
    mock_get_request = mocker.patch.object(
        dockerhub_client, "get_request", return_value={"tags": ["1.0.0"]}
    )

    dockerhub_client.do_registry_get_request(
        url_suffix="/tags/list", docker_image="demisto/python3"
    )

    mock_get_token.assert_not_called()
    call_args = mock_get_request.call_args
    headers = call_args[1].get("headers") or call_args[0][1]
    assert "Authorization" not in headers
    assert "Accept" in headers


def test_do_registry_get_request_default_registry_uses_bearer_token(
    mocker, dockerhub_client: DockerHubClient
):
    """
    Given:
        - A DockerHubClient configured with the default Docker Hub registry
          (_is_custom_registry is False)

    When:
        - running do_registry_get_request

    Then:
        - ensure get_token IS called to obtain a Docker Hub bearer token
        - ensure the Authorization header is set with the bearer token
    """
    dockerhub_client.registry_api_url = DockerHubClient.DEFAULT_REGISTRY
    dockerhub_client._is_custom_registry = False
    mock_get_token = mocker.patch.object(
        dockerhub_client, "get_token", return_value="test_token"
    )
    mock_get_request = mocker.patch.object(
        dockerhub_client, "get_request", return_value={"tags": ["1.0.0"]}
    )

    dockerhub_client.do_registry_get_request(
        url_suffix="/tags/list", docker_image="demisto/python3"
    )

    mock_get_token.assert_called_once()
    call_args = mock_get_request.call_args
    headers = call_args[1].get("headers") or call_args[0][1]
    assert headers["Authorization"] == "Bearer test_token"
    assert "Accept" in headers


def test_do_registry_get_request_gar_proxy_uses_bearer_token(
    mocker, dockerhub_client: DockerHubClient
):
    """
    Given:
        - A DockerHubClient configured with a GAR proxy registry URL
          (non-default URL, but _is_custom_registry is False because the URL
          was resolved from the DOCKER_IO env var, not user-provided)

    When:
        - running do_registry_get_request

    Then:
        - ensure get_token IS called to obtain a access token
        - ensure the Authorization header is set with the bearer token
    """
    dockerhub_client.registry_api_url = (
        "https://test-docker.pkg.dev/v2/test/test-docker"
    )
    dockerhub_client._is_custom_registry = False
    mock_get_token = mocker.patch.object(
        dockerhub_client, "get_token", return_value="test_access_token"
    )
    mock_get_request = mocker.patch.object(
        dockerhub_client, "get_request", return_value={"tags": ["1.0.0"]}
    )

    dockerhub_client.do_registry_get_request(
        url_suffix="/tags/list", docker_image="demisto/python3"
    )

    mock_get_token.assert_called_once()
    call_args = mock_get_request.call_args
    headers = call_args[1].get("headers") or call_args[0][1]
    assert headers["Authorization"] == "Bearer test_access_token"
    assert "Accept" in headers


def test_get_image_tag_metadata_custom_registry_uses_registry_api(
    mocker, dockerhub_client: DockerHubClient
):
    """
    Given:
        - A DockerHubClient configured with a user-provided custom registry
          (e.g., JFrog/Harbor), where _is_custom_registry is True

    When:
        - running get_image_tag_metadata (used by creation_date / DO106)

    Then:
        - ensure the tag metadata is fetched from the Docker Registry API
          (manifest -> config blob), NOT from the hub.docker.com web API,
          which would 404 for images that only exist on the custom registry
    """
    dockerhub_client._is_custom_registry = True
    mock_get_digest = mocker.patch.object(
        dockerhub_client, "get_image_digest", return_value="sha256:abc123"
    )
    mock_get_blobs = mocker.patch.object(
        dockerhub_client,
        "get_image_blobs",
        return_value={"created": "2023-01-01T00:00:00.000000Z"},
    )
    mock_docker_hub = mocker.patch.object(dockerhub_client, "do_docker_hub_get_request")

    response = dockerhub_client.get_image_tag_metadata(
        "xsoar-custom/python3", tag="1.0.0"
    )

    # The registry API path must be used for custom registries.
    mock_get_digest.assert_called_once_with("xsoar-custom/python3", tag="1.0.0")
    mock_get_blobs.assert_called_once_with(
        "xsoar-custom/python3", image_digest="sha256:abc123"
    )
    # The Docker Hub web API must NOT be used for custom registries.
    mock_docker_hub.assert_not_called()
    assert response == {"created": "2023-01-01T00:00:00.000000Z"}


def test_get_image_tag_metadata_default_registry_uses_docker_hub_api(
    mocker, dockerhub_client: DockerHubClient
):
    """
    Given:
        - A DockerHubClient configured with the default Docker Hub registry
          (_is_custom_registry is False, not running in CI)

    When:
        - running get_image_tag_metadata

    Then:
        - ensure the tag metadata is fetched from the hub.docker.com web API,
          preserving the original Docker Hub behavior
    """
    dockerhub_client._is_custom_registry = False
    mock_docker_hub = mocker.patch.object(
        dockerhub_client,
        "do_docker_hub_get_request",
        return_value={"last_updated": "2023-01-01T00:00:00.000000Z"},
    )
    mock_get_digest = mocker.patch.object(dockerhub_client, "get_image_digest")

    response = dockerhub_client.get_image_tag_metadata("demisto/python3", tag="1.0.0")

    mock_docker_hub.assert_called_once_with("/repositories/demisto/python3/tags/1.0.0")
    mock_get_digest.assert_not_called()
    assert response == {"last_updated": "2023-01-01T00:00:00.000000Z"}


def test_is_custom_registry_flag_gar_in_ci_is_false(monkeypatch):
    """
    Regression test for the CI GAR 401 failure.

    Given:
        - Running inside CI (IS_CONTENT_GITLAB_CI is truthy) with DOCKER_IO
          pointing at a Google Artifact Registry (GAR) proxy path, exactly as the
          DockerImage / DO104 callers construct the client
          (registry=DOCKER_REGISTRY_URL, which equals the GAR path in CI).

    When:
        - constructing a DockerHubClient through its real __init__

    Then:
        - _is_custom_registry MUST be False so the gcloud bearer token is used.
          Treating GAR as a custom registry skips the bearer token and causes a
          401 Unauthorized against the GAR proxy.
    """
    gar_path = "test.pkg.dev/test/" "test-docker-hub-virtual"
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.IS_CONTENT_GITLAB_CI", "true")
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.DOCKER_IO", gar_path)

    # Use a unique docker_hub_api_url to avoid the @lru_cache returning a cached
    # instance built under different env conditions in another test.
    client = DockerHubClient(
        docker_hub_api_url="https://gar-ci-test.example/v2",
        registry=gar_path,
    )

    assert client._is_custom_registry is False
    registry_host = urlparse(client.registry_api_url).hostname
    assert registry_host and registry_host.endswith(".pkg.dev")


def test_is_custom_registry_flag_gar_local_not_in_ci_is_false(monkeypatch):
    """
    Regression test for the local (non-CI) GAR 401 failure on demistoextended.

    Given:
        - NOT running in CI (IS_CONTENT_GITLAB_CI is falsy) with a GAR
          gcr.io/xsoar-registry target, as the extended DockerImage client builds
          it for demistoextended images.

    When:
        - constructing a DockerHubClient through its real __init__

    Then:
        - _is_custom_registry MUST be False so the gcloud bearer token is used,
          even locally. Treating gcr.io as a custom registry would send Basic Auth
          and yield a 401 Unauthorized.
    """
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.IS_CONTENT_GITLAB_CI", None)
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.DOCKER_IO", "")

    client = DockerHubClient(
        docker_hub_api_url="https://gar-local-test.example/v2",
        registry="gcr.io/xsoar-registry",
    )

    assert client._is_custom_registry is False
    registry_host = urlparse(client.registry_api_url).hostname
    assert registry_host == "gcr.io"


def test_get_token_uses_gcloud_for_gar_registry_locally(mocker, monkeypatch):
    """
    Given:
        - NOT running in CI, with a GAR gcr.io registry (demistoextended target).

    When:
        - get_token is called.

    Then:
        - The gcloud access token is used, not the Docker Hub token endpoint.
    """
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.IS_CONTENT_GITLAB_CI", None)
    mock_gcloud = mocker.patch(
        f"{_DOCKERHUB_CLIENT_MODULE}.get_gcloud_access_token",
        return_value="gcloud-token-123",
    )
    client = DockerHubClient(
        docker_hub_api_url="https://gar-token-test.example/v2",
        registry="gcr.io/xsoar-registry",
    )

    token = client.get_token("demistoextended/accessdata-p")

    assert token == "gcloud-token-123"
    mock_gcloud.assert_called_once()


def test_is_custom_registry_flag_customer_registry_not_in_ci_is_true(monkeypatch):
    """
    Given:
        - NOT running in CI (IS_CONTENT_GITLAB_CI is falsy) and a user-provided
          custom registry URL (e.g., a JFrog/Harbor host:port), as configured by a
          customer via DEMISTO_SDK_CONTAINER_REGISTRY.

    When:
        - constructing a DockerHubClient through its real __init__

    Then:
        - _is_custom_registry MUST be True so Basic Auth is used for the custom registry
    """
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.IS_CONTENT_GITLAB_CI", None)
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.DOCKER_IO", "")

    client = DockerHubClient(
        docker_hub_api_url="https://customreg-test.example/v2",
        registry="https://my-jfrog.example.com:8443",
    )

    assert client._is_custom_registry is True
    assert client.registry_api_url == "https://my-jfrog.example.com:8443/v2"


def test_is_custom_registry_flag_default_registry_is_false(monkeypatch):
    """
    Given:
        - NOT running in CI and no custom registry provided (empty registry),
          i.e., the local Docker Hub default scenario.

    When:
        - constructing a DockerHubClient through its real __init__

    Then:
        - _is_custom_registry MUST be False so the Docker Hub bearer token is used.
    """
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.IS_CONTENT_GITLAB_CI", None)
    monkeypatch.setattr(f"{_DOCKERHUB_CLIENT_MODULE}.DOCKER_IO", "")

    client = DockerHubClient(
        docker_hub_api_url="https://default-test.example/v2",
        registry="",
    )

    assert client._is_custom_registry is False
    assert client.registry_api_url == DockerHubClient.DEFAULT_REGISTRY

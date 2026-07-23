import os
from unittest import mock

import pytest
import requests
from packaging.version import Version

import demisto_sdk.commands.common.docker_helper as dhelper


def test_init_global_docker_client():
    res = dhelper.init_global_docker_client(log_prompt="unit testing")
    assert res is not None
    assert res == dhelper.DOCKER_CLIENT
    dhelper.DOCKER_CLIENT = None
    # test with bad creds (should still get a valid instance)
    with mock.patch.dict(
        os.environ, {"DOCKERHUB_USER": "dummy", "DOCKERHUB_PASSWORD": "dummy"}
    ):
        res = dhelper.init_global_docker_client(log_prompt="unit testing")
        assert res is not None
        assert res == dhelper.DOCKER_CLIENT


@pytest.mark.parametrize(
    argnames="image, output, expected",
    argvalues=[
        ("alpine", "3.7.11", "3.7.11"),
        ("alpine-3", "2.7.1", "2.7.1"),
        ("alpine-310", "3.10.11", "3.10.11"),
        ("demisto/python3:3.9.8.24399", "", "3.9.8"),
        ("demisto/python:2.7.18.24398", "", "2.7.18"),
        ("demisto/pan-os-python:1.0.0.68955", "3.10.12", "3.10.12"),
        ("demisto/powershell:7.1.3.22028", "", None),
    ],
)
def test_get_python_version_from_image(image: str, output: str, expected: str, mocker):
    from demisto_sdk.commands.common import docker_helper
    from demisto_sdk.commands.common.files.file import File

    class ImageMock:
        def __init__(self, attrs):
            self.attrs = attrs

    mocker.patch.object(docker_helper, "init_global_docker_client")
    mocker.patch.object(
        File,
        "read_from_github_api",
        return_value={
            "docker_images": {
                "python3": {
                    "3.10.11.54799": {"python_version": "3.10.11"},
                    "3.10.12.63474": {"python_version": "3.10.11"},
                }
            }
        },
    )
    mocker.patch(
        "demisto_sdk.commands.common.docker_helper._get_python_version_from_dockerhub_api",
        side_effect=Exception("rate limit"),
    )
    docker_helper.init_global_docker_client().images.get.return_value = ImageMock(
        {"Config": {"Env": [f"PYTHON_VERSION={output}"]}}
    )
    result = Version(expected) if expected is not None else None
    assert result == docker_helper.get_python_version(image)


def test_cache_of_get_python_version_from_image():
    """
    Given -
        docker image that should be already cached

    When -
        Try to get python version from am docker image

    Then -
        Validate the value returned from the cache
    """
    from demisto_sdk.commands.common import docker_helper

    image = "demisto/python3:3.9.8.12345"

    cache_info_before = docker_helper.get_python_version.cache_info()
    docker_helper.get_python_version(image)
    cache_info = docker_helper.get_python_version.cache_info()
    assert cache_info.hits == cache_info_before.hits

    docker_helper.get_python_version(image)
    cache_info = docker_helper.get_python_version.cache_info()
    assert cache_info.hits == cache_info_before.hits + 1


class DockerClientMock:
    def __init__(self):
        # mock the function login
        self.login = mock.MagicMock()

    def ping(self):
        return True


def test_custom_container_registry(mocker):
    """
    Given:
        - Custom container registry

    When:
        - Running the init_global_docker_client function

    Then:
        - Ensure the login function is called with the correct parameters

    """
    from demisto_sdk.commands.common import docker_helper

    docker_client_mock = DockerClientMock()
    mocker.patch.object(docker_helper, "DOCKER_REGISTRY_URL", "custom")
    mocker.patch.dict(
        os.environ,
        {
            "DEMISTO_SDK_CONTAINER_REGISTRY": "custom",
            "DEMISTO_SDK_CR_USER": "user",
            "DEMISTO_SDK_CR_PASSWORD": "password",
        },
    )
    assert docker_helper.is_custom_registry()
    docker_helper.docker_login(docker_client_mock)
    assert docker_client_mock.login.called
    assert docker_client_mock.login.call_count == 1
    assert docker_client_mock.login.call_args[1] == {
        "username": "user",
        "password": "password",
        "registry": "custom",
    }


@pytest.mark.parametrize(
    "image_name, container_name, exception, exception_text",
    [
        (
            "demisto_test:1234",
            "test",
            requests.exceptions.ConnectionError,
            "Connection error",
        ),
        ("demisto_test:1234", "test", requests.exceptions.Timeout, "Timeout error"),
        ("demisto_test:1234", "test", dhelper.DockerException, "Docker exception"),
    ],
)
def test_create_docker_container_successfully(
    mocker, image_name, container_name, exception, exception_text
):
    """
    Given -
        Docker client and docker image name

    When -
        Try to create docker container

    Then -
        Validate the re-run works as expected
            1. Getting ConnectionError
            2. Getting Timeout error
            3. Getting Docker error
    """

    class MockContainer:
        @staticmethod
        def remove(**kwargs):
            assert kwargs.get("force")
            raise exception(exception_text)

    class MockContainerCollection:
        @staticmethod
        def create(**kwargs):
            assert kwargs.get("image") == image_name
            assert kwargs.get("name") == container_name
            raise exception(exception_text)

        @staticmethod
        def get(**kwargs):
            assert kwargs.get("container_id") == container_name
            return MockContainer()

    class MockedDockerClient:
        containers = MockContainerCollection()

    mocker.patch(
        "demisto_sdk.commands.common.docker_helper.init_global_docker_client",
        return_value=MockedDockerClient,
    )
    log_result = mocker.patch("demisto_sdk.commands.common.tools.logger.debug")

    with pytest.raises(exception):
        dhelper.DockerBase().create_container(image=image_name, name=container_name)

    assert (
        f"error when executing func create_container, error: {exception_text}, time 3"
        in log_result.call_args.args
    )


def test_push_image_when_push_succeeds_verifies_image(mocker):
    """
    Given:
        - A docker client whose push returns a successful (no errorDetail) output.
    When:
        - push_image is called.
    Then:
        - The image is pushed once (registry prefix stripped) and the post-push
          verification is invoked with the stripped image name.
    """
    # Given: a client that pushes successfully and a stubbed verification step
    push_mock = mock.MagicMock(return_value="pushed layer\r\nlatest: digest: sha256")
    client_mock = mock.MagicMock()
    client_mock.images.push = push_mock
    mocker.patch.object(dhelper, "init_global_docker_client", return_value=client_mock)
    verify_mock = mocker.patch.object(
        dhelper.DockerBase, "_verify_image_available_after_push"
    )

    # When: pushing an image that carries the registry prefix
    dhelper.DockerBase().push_image(
        f"{dhelper.DOCKER_REGISTRY_URL}/devtestdemisto/python3:1.0.0", log_prompt="lp"
    )

    # Then: the registry prefix is stripped and verification is triggered
    push_mock.assert_called_once_with("devtestdemisto/python3:1.0.0")
    verify_mock.assert_called_once_with("devtestdemisto/python3:1.0.0", log_prompt="lp")


def test_push_image_when_all_attempts_fail_raises(mocker):
    """
    Given:
        - A docker client whose push always raises a connection error.
    When:
        - push_image is called.
    Then:
        - A DockerException is raised indicating all push attempts failed and
          verification is never attempted.
    """
    # Given: a client that always fails to push with a retryable network error
    client_mock = mock.MagicMock()
    client_mock.images.push.side_effect = requests.exceptions.ConnectionError("boom")
    mocker.patch.object(dhelper, "init_global_docker_client", return_value=client_mock)
    verify_mock = mocker.patch.object(
        dhelper.DockerBase, "_verify_image_available_after_push"
    )

    # When / Then: all attempts exhausted -> DockerException, no verification
    with pytest.raises(dhelper.DockerException, match="All push attempts failed"):
        dhelper.DockerBase().push_image("devtestdemisto/python3:1.0.0")

    assert client_mock.images.push.call_count == 2
    verify_mock.assert_not_called()


def test_push_image_when_output_has_error_detail_raises(mocker):
    """
    Given:
        - A docker client whose push output contains an errorDetail line.
    When:
        - push_image is called.
    Then:
        - A DockerException is raised indicating the push failed and verification
          is never attempted.
    """
    # Given: push output that reports an errorDetail
    client_mock = mock.MagicMock()
    client_mock.images.push.return_value = (
        'layer\r\n{"errorDetail": {"message": "denied"}}'
    )
    mocker.patch.object(dhelper, "init_global_docker_client", return_value=client_mock)
    verify_mock = mocker.patch.object(
        dhelper.DockerBase, "_verify_image_available_after_push"
    )

    # When / Then: errorDetail present -> DockerException, no verification
    with pytest.raises(dhelper.DockerException, match="Failed to push image"):
        dhelper.DockerBase().push_image("devtestdemisto/python3:1.0.0")

    verify_mock.assert_not_called()


def test_verify_image_available_after_push_when_available_returns(mocker):
    """
    Given:
        - A tagged image whose token and digest lookups succeed on the first try.
    When:
        - _verify_image_available_after_push is called.
    Then:
        - The repo/tag are parsed correctly, no delay occurs, and it returns
          without raising.
    """
    # Given: successful token + digest lookup
    token_mock = mocker.patch.object(
        dhelper, "_get_docker_hub_token", return_value="tok"
    )
    digest_mock = mocker.patch.object(
        dhelper, "_get_image_digest", return_value="sha256:abc"
    )
    sleep_mock = mocker.patch.object(dhelper.time, "sleep")

    # When
    dhelper.DockerBase._verify_image_available_after_push("devtestdemisto/python3:1.0.0")

    # Then
    token_mock.assert_called_once_with("devtestdemisto/python3")
    digest_mock.assert_called_once_with("devtestdemisto/python3", "1.0.0", "tok")
    sleep_mock.assert_not_called()


def test_verify_image_available_after_push_when_untagged_uses_latest(mocker):
    """
    Given:
        - An image name without a tag.
    When:
        - _verify_image_available_after_push is called.
    Then:
        - The tag defaults to 'latest' when querying the digest.
    """
    # Given
    mocker.patch.object(dhelper, "_get_docker_hub_token", return_value="tok")
    digest_mock = mocker.patch.object(
        dhelper, "_get_image_digest", return_value="sha256:abc"
    )
    mocker.patch.object(dhelper.time, "sleep")

    # When
    dhelper.DockerBase._verify_image_available_after_push("devtestdemisto/python3")

    # Then
    digest_mock.assert_called_once_with("devtestdemisto/python3", "latest", "tok")


def test_verify_image_available_after_push_retries_then_succeeds(mocker):
    """
    Given:
        - Digest lookup that raises RuntimeError once, then succeeds.
    When:
        - _verify_image_available_after_push is called.
    Then:
        - It retries after sleeping once and returns successfully.
    """
    # Given: first attempt not-yet-propagated, second attempt available
    mocker.patch.object(dhelper, "_get_docker_hub_token", return_value="tok")
    digest_mock = mocker.patch.object(
        dhelper,
        "_get_image_digest",
        side_effect=[RuntimeError("not found"), "sha256:abc"],
    )
    sleep_mock = mocker.patch.object(dhelper.time, "sleep")

    # When
    dhelper.DockerBase._verify_image_available_after_push(
        "devtestdemisto/python3:1.0.0", delay_seconds=30
    )

    # Then
    assert digest_mock.call_count == 2
    sleep_mock.assert_called_once_with(30)


def test_verify_image_available_after_push_when_never_available_raises(mocker):
    """
    Given:
        - Digest lookup that always raises RuntimeError.
    When:
        - _verify_image_available_after_push is called with a small retry budget.
    Then:
        - A DockerException is raised after exhausting retries, sleeping only
          between attempts (max_retries - 1 times).
    """
    # Given: image never becomes available
    mocker.patch.object(dhelper, "_get_docker_hub_token", return_value="tok")
    mocker.patch.object(
        dhelper, "_get_image_digest", side_effect=RuntimeError("not found")
    )
    sleep_mock = mocker.patch.object(dhelper.time, "sleep")

    # When / Then
    with pytest.raises(dhelper.DockerException, match="Image verification failed"):
        dhelper.DockerBase._verify_image_available_after_push(
            "devtestdemisto/python3:1.0.0", max_retries=3, delay_seconds=5
        )

    assert sleep_mock.call_count == 2


def test_verify_image_available_after_push_retries_on_network_error(mocker):
    """
    Given:
        - Token lookup that raises a network error once, then digest succeeds.
    When:
        - _verify_image_available_after_push is called.
    Then:
        - The network error is caught, it sleeps once, and then succeeds.
    """
    # Given: first attempt hits a connection error, second succeeds
    mocker.patch.object(
        dhelper,
        "_get_docker_hub_token",
        side_effect=[requests.exceptions.ConnectionError("net"), "tok"],
    )
    mocker.patch.object(dhelper, "_get_image_digest", return_value="sha256:abc")
    sleep_mock = mocker.patch.object(dhelper.time, "sleep")

    # When
    dhelper.DockerBase._verify_image_available_after_push("devtestdemisto/python3:1.0.0")

    # Then
    sleep_mock.assert_called_once()

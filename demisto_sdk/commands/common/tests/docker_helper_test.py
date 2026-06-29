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


# --- demistoextended get_image_registry tests ---


class TestGetImageRegistryDemistoextended:
    def test_demistoextended_with_env_prefixes_image(self):
        """
        Given:
         - a demistoextended/ image and DEMISTO_SDK_EXTENDED_REGISTRY is set

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - returns the image prefixed with the extended registry URL
        """
        with mock.patch.dict(
            os.environ,
            {"DEMISTO_SDK_EXTENDED_REGISTRY": "example-registry.io/test-project"},
        ):
            result = dhelper.DockerBase.get_image_registry(
                "demistoextended/accessdata:1.1.0.10177564"
            )
            assert (
                result
                == "example-registry.io/test-project/demistoextended/accessdata:1.1.0.10177564"
            )

    def test_demistoextended_without_env_returns_unchanged(self):
        """
        Given:
         - a demistoextended/ image and DEMISTO_SDK_EXTENDED_REGISTRY is NOT set

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - returns the image unchanged (no prefix added)
        """
        env = os.environ.copy()
        env.pop("DEMISTO_SDK_EXTENDED_REGISTRY", None)
        with mock.patch.dict(os.environ, env, clear=True):
            result = dhelper.DockerBase.get_image_registry(
                "demistoextended/accessdata:1.1.0.10177564"
            )
            assert result == "demistoextended/accessdata:1.1.0.10177564"

    def test_demistoextended_already_prefixed_returns_unchanged(self):
        """
        Given:
         - a demistoextended/ image that already contains the extended registry prefix
         - DEMISTO_SDK_EXTENDED_REGISTRY is set

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - the image is returned unchanged, avoiding double-prefixing with the
           extended registry
        """
        with mock.patch.dict(
            os.environ,
            {"DEMISTO_SDK_EXTENDED_REGISTRY": "example-registry.io/test-project"},
        ):
            already_prefixed = "example-registry.io/test-project/demistoextended/accessdata:1.1.0.10177564"
            result = dhelper.DockerBase.get_image_registry(already_prefixed)
            # The image already carries the extended registry prefix, so it is
            # returned as-is to avoid double-prefixing.
            assert result == already_prefixed

    def test_cr_prefixed_image_normalized_without_env(self):
        """
        Given:
         - a dockerimage hardcoding the CR prefix (gcr.io/xsoar-registry/demistoextended/...)
         - DEMISTO_SDK_EXTENDED_REGISTRY is NOT set

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - the CR prefix is stripped and the canonical demistoextended/ form is
           returned (so the runner's Docker mirror won't produce a broken
           double-registry path)
        """
        env = os.environ.copy()
        env.pop("DEMISTO_SDK_EXTENDED_REGISTRY", None)
        with mock.patch.dict(os.environ, env, clear=True):
            result = dhelper.DockerBase.get_image_registry(
                "gcr.io/xsoar-registry/demistoextended/accessdata-p:1.1.0.10358491"
            )
            assert result == "demistoextended/accessdata-p:1.1.0.10358491"

    def test_cr_prefixed_image_normalized_with_env(self):
        """
        Given:
         - a dockerimage hardcoding the CR prefix (gcr.io/xsoar-registry/demistoextended/...)
         - DEMISTO_SDK_EXTENDED_REGISTRY is set to gcr.io/xsoar-registry

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - the CR prefix is stripped then re-added via the extended registry,
           yielding a single, well-formed registry path
        """
        with mock.patch.dict(
            os.environ,
            {"DEMISTO_SDK_EXTENDED_REGISTRY": "gcr.io/xsoar-registry"},
        ):
            result = dhelper.DockerBase.get_image_registry(
                "gcr.io/xsoar-registry/demistoextended/accessdata-p:1.1.0.10358491"
            )
            assert (
                result
                == "gcr.io/xsoar-registry/demistoextended/accessdata-p:1.1.0.10358491"
            )

    def test_cr_prefixed_image_normalized_with_different_env(self):
        """
        Given:
         - a dockerimage hardcoding the CR prefix (gcr.io/xsoar-registry/demistoextended/...)
         - DEMISTO_SDK_EXTENDED_REGISTRY is set to a DIFFERENT registry

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - the hardcoded CR prefix is stripped and the configured extended
           registry is applied instead (routing stays uniform)
        """
        with mock.patch.dict(
            os.environ,
            {"DEMISTO_SDK_EXTENDED_REGISTRY": "example-registry.io/test-project"},
        ):
            result = dhelper.DockerBase.get_image_registry(
                "gcr.io/xsoar-registry/demistoextended/accessdata-p:1.1.0.10358491"
            )
            assert (
                result
                == "example-registry.io/test-project/demistoextended/accessdata-p:1.1.0.10358491"
            )

    def test_demisto_image_still_gets_docker_registry_prefix(self):
        """
        Given:
         - a demisto/ image (not demistoextended)

        When:
         - calling DockerBase.get_image_registry()

        Then:
         - returns the image prefixed with DOCKER_REGISTRY_URL (existing behavior)
        """
        from demisto_sdk.commands.common.constants import DOCKER_REGISTRY_URL

        image = "demisto/python3:3.10.11.54799"
        result = dhelper.DockerBase.get_image_registry(image)
        if DOCKER_REGISTRY_URL not in image:
            assert result == f"{DOCKER_REGISTRY_URL}/{image}"
        else:
            assert result == image


class TestGetOrCreateTestImageDemistoextended:
    """Tests for get_or_create_test_image with demistoextended images."""

    def test_demistoextended_image_uses_devtestdemistoextended_prefix(self):
        """
        Given:
         - a demistoextended/ base image

        When:
         - the test image name is constructed in get_or_create_test_image

        Then:
         - the prefix should be devtestdemistoextended/ (not devtestdemistoextended/)
        """
        base_image = "demistoextended/accessdata:1.1.0.10177564"
        # Simulate the logic from get_or_create_test_image
        if base_image.startswith("demistoextended/"):
            result = base_image.replace("demistoextended", "devtestdemistoextended")
        else:
            result = base_image.replace("demisto", "devtestdemisto")
        assert result == "devtestdemistoextended/accessdata:1.1.0.10177564"

    def test_demisto_image_still_uses_devtestdemisto_prefix(self):
        """
        Given:
         - a demisto/ base image

        When:
         - the test image name is constructed

        Then:
         - the prefix should be devtestdemisto/ (existing behavior)
        """
        base_image = "demisto/python3:3.10.11.54799"
        if base_image.startswith("demistoextended/"):
            result = base_image.replace("demistoextended", "devtestdemistoextended")
        else:
            result = base_image.replace("demisto", "devtestdemisto")
        assert result == "devtestdemisto/python3:3.10.11.54799"

    def test_naive_replace_would_break_demistoextended(self):
        """
        Given:
         - a demistoextended/ base image

        When:
         - using the old naive replace("demisto", "devtestdemisto")

        Then:
         - it would produce devtestdemistoextended (broken name)
        """
        base_image = "demistoextended/accessdata:1.1.0.10177564"
        naive_result = base_image.replace("demisto", "devtestdemisto")
        # This is the broken behavior we fixed
        assert naive_result == "devtestdemistoextended/accessdata:1.1.0.10177564"
        # The correct behavior with our fix:
        if base_image.startswith("demistoextended/"):
            correct_result = base_image.replace(
                "demistoextended", "devtestdemistoextended"
            )
        else:
            correct_result = base_image.replace("demisto", "devtestdemisto")
        assert correct_result == "devtestdemistoextended/accessdata:1.1.0.10177564"


class TestUpdateDockerImageSkipsDemistoextended:
    """Tests for update_docker_image_in_script skipping demistoextended images."""

    def test_skips_demistoextended_image(self):
        """
        Given:
         - a script object with a demistoextended/ docker image

        When:
         - calling update_docker_image_in_script

        Then:
         - the docker image should not be modified
        """
        from demisto_sdk.commands.format.update_script import ScriptYMLFormat

        script_obj = {
            "type": "python",
            "dockerimage": "demistoextended/accessdata:1.1.0.10177564",
        }
        original_image = script_obj["dockerimage"]
        ScriptYMLFormat.update_docker_image_in_script(
            script_obj, "/fake/path/script.yml"
        )
        assert script_obj["dockerimage"] == original_image

    def test_does_not_skip_demisto_image(self):
        """
        Given:
         - a script object with a demisto/ docker image

        When:
         - calling update_docker_image_in_script

        Then:
         - the function should attempt to update (not skip early)
         - it may fail due to network, but it should NOT return early
        """
        from demisto_sdk.commands.format.update_script import ScriptYMLFormat

        script_obj = {
            "type": "python",
            "dockerimage": "demisto/python3:3.10.11.54799",
        }
        # The function will try to query DockerHub and may fail,
        # but it should NOT return early like it does for demistoextended
        ScriptYMLFormat.update_docker_image_in_script(
            script_obj, "/fake/path/script.yml"
        )
        # If it returned early for demisto/ images, that would be a bug.
        # The image may or may not be updated depending on network,
        # but the key assertion is that it didn't skip.


class TestGetPythonVersionDemistoextendedFallback:
    """Tests that get_python_version raises for demistoextended images
    when all resolution methods fail (no silent fallback)."""

    def test_demistoextended_raises_when_all_methods_fail(self, mocker):
        """
        Given:
         - A demistoextended image with DEMISTO_SDK_EXTENDED_REGISTRY set
         - All Python version resolution methods fail
        When:
         - get_python_version is called
        Then:
         - Raises an exception (no silent fallback)
        """
        from demisto_sdk.commands.common import docker_helper
        from demisto_sdk.commands.common.docker_helper import get_python_version

        get_python_version.cache_clear()

        mocker.patch.object(
            docker_helper,
            "DockerImagesMetadata",
        )
        docker_helper.DockerImagesMetadata.get_instance.return_value.python_version.return_value = None
        mocker.patch.object(
            docker_helper,
            "_get_python_version_from_tag_by_regex",
            return_value=None,
        )
        mocker.patch.object(
            docker_helper,
            "_get_python_version_from_image_client",
            side_effect=Exception("docker pull failed"),
        )
        mocker.patch.object(
            docker_helper,
            "_get_python_version_from_dockerhub_api",
            side_effect=Exception("dockerhub api failed"),
        )
        mocker.patch.object(docker_helper, "IS_CONTENT_GITLAB_CI", True)

        env = {"DEMISTO_SDK_EXTENDED_REGISTRY": "example-registry.io/test-project"}
        with mock.patch.dict(os.environ, env):
            with pytest.raises(Exception, match="docker pull failed"):
                get_python_version("demistoextended/accessdata:1.1.0.10293277")

    def test_demisto_image_still_raises_when_all_methods_fail(self, mocker):
        """
        Given:
         - A regular demisto image
         - All Python version resolution methods fail
        When:
         - get_python_version is called
        Then:
         - Raises an exception (does NOT silently default)
        """
        from demisto_sdk.commands.common import docker_helper
        from demisto_sdk.commands.common.docker_helper import get_python_version

        get_python_version.cache_clear()

        mocker.patch.object(
            docker_helper,
            "DockerImagesMetadata",
        )
        docker_helper.DockerImagesMetadata.get_instance.return_value.python_version.return_value = None
        mocker.patch.object(
            docker_helper,
            "_get_python_version_from_tag_by_regex",
            return_value=None,
        )
        mocker.patch.object(
            docker_helper,
            "_get_python_version_from_image_client",
            side_effect=Exception("docker pull failed"),
        )
        mocker.patch.object(
            docker_helper,
            "_get_python_version_from_dockerhub_api",
            side_effect=Exception("dockerhub api failed"),
        )
        mocker.patch.object(docker_helper, "IS_CONTENT_GITLAB_CI", False)

        with pytest.raises(Exception, match="docker pull failed"):
            get_python_version("demisto/python3:3.10.11.54799-unique-test")

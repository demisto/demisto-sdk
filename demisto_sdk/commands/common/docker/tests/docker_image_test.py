import os
from unittest.mock import MagicMock, patch

import pytest

from demisto_sdk.commands.common.docker.docker_image import DockerImage


@pytest.mark.parametrize(
    "docker_image, expected_repo, expected_image_name, expected_tag",
    [
        (
            "demisto/pan-os-python:1.0.0.83880",
            "demisto",
            "pan-os-python",
            "1.0.0.83880",
        ),
        ("demisto/py3-tools:0.0.1.25751", "demisto", "py3-tools", "0.0.1.25751"),
        ("demisto/boto3py3:1.0.0.52713", "demisto", "boto3py3", "1.0.0.52713"),
        (
            "demisto/googleapi-python3:1.0.0.12698",
            "demisto",
            "googleapi-python3",
            "1.0.0.12698",
        ),
        ("demisto/ml:1.0.0.84027", "demisto", "ml", "1.0.0.84027"),
        ("demisto/fetch-data:1.0.0.22177", "demisto", "fetch-data", "1.0.0.22177"),
        ("demisto/python3:3.10.13.78960", "demisto", "python3", "3.10.13.78960"),
        ("custom-repo/test-image:7.8.9", "custom-repo", "test-image", "7.8.9"),
        ("some-repo/test-image-2:1.1.1.1", "some-repo", "test-image-2", "1.1.1.1"),
    ],
)
def test_docker_image_parse_valid_docker_images(
    docker_image: str, expected_repo: str, expected_image_name: str, expected_tag: str
):
    """
    Given:
     - valid docker images

    When:
    - trying to parse docker-images parts (repository, image-name and tag)

    Then:
    - make sure images are parsed correctly
    """
    docker_image_object = DockerImage(docker_image)
    assert docker_image_object.repository == expected_repo
    assert docker_image_object.image_name == expected_image_name
    assert docker_image_object.tag == expected_tag


@pytest.mark.parametrize(
    "docker_image",
    [
        "demisto/pan-os-python",
        "demisto",
        "1.0.0.52713",
        "test-image:7.8.9",
        "some-repo",
    ],
)
def test_docker_image_parse_invalid_docker_images(docker_image: str):
    """
    Given:
     - invalid docker images

    When:
    - trying to parse docker-images parts (repository, image-name and tag)

    Then:
    - make sure ValueError is raised
    """
    with pytest.raises(ValueError):
        DockerImage(docker_image, raise_if_not_valid=True)


# --- demistoextended / trusted repository tests ---


@pytest.fixture(autouse=False)
def _reset_extended_client():
    """Reset the singleton _extended_client before and after each test that uses it."""
    DockerImage._extended_client = None
    yield
    DockerImage._extended_client = None


class TestIsDemistoextendedRepository:
    def test_demistoextended_image_returns_true(self):
        """
        Given:
         - a docker image from the demistoextended repository

        When:
         - checking is_demistoextended_repository

        Then:
         - returns True
        """
        image = DockerImage("demistoextended/accessdata:1.1.0.10177564")
        assert image.is_demistoextended_repository is True

    def test_demisto_image_returns_false(self):
        """
        Given:
         - a docker image from the demisto repository

        When:
         - checking is_demistoextended_repository

        Then:
         - returns False
        """
        image = DockerImage("demisto/python3:3.10.11.54799")
        assert image.is_demistoextended_repository is False


class TestIsTrustedRepository:
    def test_demisto_is_trusted(self):
        """
        Given:
         - a docker image from the demisto repository

        When:
         - checking is_trusted_repository

        Then:
         - returns True
        """
        image = DockerImage("demisto/python3:3.10.11.54799")
        assert image.is_trusted_repository is True

    def test_demistoextended_is_trusted(self):
        """
        Given:
         - a docker image from the demistoextended repository

        When:
         - checking is_trusted_repository

        Then:
         - returns True
        """
        image = DockerImage("demistoextended/accessdata:1.1.0.10177564")
        assert image.is_trusted_repository is True

    def test_unknown_repo_is_not_trusted(self):
        """
        Given:
         - a docker image from an unknown repository

        When:
         - checking is_trusted_repository

        Then:
         - returns False
        """
        image = DockerImage("someother/image:1.0")
        assert image.is_trusted_repository is False


class TestGetExtendedClient:
    @pytest.mark.usefixtures("_reset_extended_client")
    def test_with_env_var_returns_client(self):
        """
        Given:
         - DEMISTO_SDK_EXTENDED_REGISTRY env var is set

        When:
         - calling _get_extended_client()

        Then:
         - returns a DockerHubClient instance (not None)
        """
        with patch.dict(
            os.environ,
            {"DEMISTO_SDK_EXTENDED_REGISTRY": "example-registry.io/test-project"},
        ):
            client = DockerImage._get_extended_client()
            assert client is not None
            # DockerHubClient is @lru_cache-wrapped so isinstance() won't work;
            # verify by checking a known attribute instead.
            assert hasattr(client, "registry_api_url")
            # The override this method exists to produce: the extended registry
            # (host/project) is turned into the V2 API URL host/v2/project.
            assert (
                client.registry_api_url == "https://example-registry.io/v2/test-project"
            )

    @pytest.mark.usefixtures("_reset_extended_client")
    def test_without_env_var_uses_default_registry(self):
        """
        Given:
         - DEMISTO_SDK_EXTENDED_REGISTRY env var is NOT set

        When:
         - calling _get_extended_client()

        Then:
         - a client is still created using the default extended registry
           (gcr.io/xsoar-registry), not None
        """
        with patch.dict(os.environ, {}, clear=False):
            # Ensure the env var is absent
            os.environ.pop("DEMISTO_SDK_EXTENDED_REGISTRY", None)
            client = DockerImage._get_extended_client()
            assert client is not None
            assert client.registry_api_url == "https://gcr.io/v2/xsoar-registry"


class TestGetClient:
    @pytest.mark.usefixtures("_reset_extended_client")
    def test_routes_to_extended_for_demistoextended(self):
        """
        Given:
         - a demistoextended/ image and DEMISTO_SDK_EXTENDED_REGISTRY is set

        When:
         - calling _get_client()

        Then:
         - returns the extended client, not the default dockerhub client
        """
        mock_extended = MagicMock(name="extended_client")
        mock_dockerhub = MagicMock(name="dockerhub_client")

        with (
            patch.object(
                DockerImage, "_get_extended_client", return_value=mock_extended
            ),
            patch.object(
                DockerImage, "_get_dockerhub_client", return_value=mock_dockerhub
            ),
        ):
            image = DockerImage("demistoextended/accessdata:1.1.0.10177564")
            client = image._get_client()
            assert client is mock_extended

    @pytest.mark.usefixtures("_reset_extended_client")
    def test_falls_back_to_dockerhub_for_demisto(self):
        """
        Given:
         - a demisto/ image (not demistoextended)

        When:
         - calling _get_client()

        Then:
         - returns the default dockerhub client regardless of extended registry config
        """
        mock_extended = MagicMock(name="extended_client")
        mock_dockerhub = MagicMock(name="dockerhub_client")

        with (
            patch.object(
                DockerImage, "_get_extended_client", return_value=mock_extended
            ),
            patch.object(
                DockerImage, "_get_dockerhub_client", return_value=mock_dockerhub
            ),
        ):
            image = DockerImage("demisto/python3:3.10.11.54799")
            client = image._get_client()
            assert client is mock_dockerhub

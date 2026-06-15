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


class TestDemistoprivateRepository:
    """Tests for demistoextended repository support in DockerImage."""

    def test_is_demistoextended_repository(self):
        """
        Given:
         - A docker image from the demistoextended repository.

        When:
         - Checking is_demistoextended_repository.

        Then:
         - Returns True.
        """
        image = DockerImage("demistoextended/generic-sql:1.2.0.10029029")
        assert image.is_demistoextended_repository is True
        assert image.is_demisto_repository is False

    def test_is_not_demistoextended_repository(self):
        """
        Given:
         - A docker image from the demisto repository.

        When:
         - Checking is_demistoextended_repository.

        Then:
         - Returns False.
        """
        image = DockerImage("demisto/python3:3.10.13.78960")
        assert image.is_demistoextended_repository is False
        assert image.is_demisto_repository is True

    @pytest.mark.parametrize(
        "docker_image, expected",
        [
            ("demisto/python3:3.10.13.78960", True),
            ("demistoextended/generic-sql:1.2.0.10029029", True),
            ("custom-repo/test-image:7.8.9", False),
        ],
    )
    def test_is_trusted_repository(self, docker_image: str, expected: bool):
        """
        Given:
         - Docker images from demisto, demistoextended, and custom repositories.

        When:
         - Checking is_trusted_repository.

        Then:
         - Returns True for demisto and demistoextended, False for others.
        """
        assert DockerImage(docker_image).is_trusted_repository is expected

    def test_is_image_exist_returns_true_for_private(self):
        """
        Given:
         - A demistoextended docker image.

        When:
         - Checking is_image_exist.

        Then:
         - Returns True without querying DockerHub.
        """
        image = DockerImage("demistoextended/generic-sql:1.2.0.10029029")
        assert image.is_image_exist is True

    def test_creation_date_returns_none_for_private(self):
        """
        Given:
         - A demistoextended docker image.

        When:
         - Accessing creation_date.

        Then:
         - Returns None without querying DockerHub.
        """
        image = DockerImage("demistoextended/generic-sql:1.2.0.10029029")
        assert image.creation_date is None

    def test_latest_tag_returns_current_tag_for_private(self):
        """
        Given:
         - A demistoextended docker image with tag 1.2.0.10029029.

        When:
         - Accessing latest_tag.

        Then:
         - Returns the current tag as a Version.
        """
        from packaging.version import Version

        image = DockerImage("demistoextended/generic-sql:1.2.0.10029029")
        assert image.latest_tag == Version("1.2.0.10029029")

    def test_latest_docker_image_returns_self_for_private(self):
        """
        Given:
         - A demistoextended docker image.

        When:
         - Accessing latest_docker_image.

        Then:
         - Returns self (the same image).
        """
        image = DockerImage("demistoextended/generic-sql:1.2.0.10029029")
        assert image.latest_docker_image == image
        assert str(image.latest_docker_image) == "demistoextended/generic-sql:1.2.0.10029029"

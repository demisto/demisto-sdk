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

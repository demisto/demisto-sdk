from typing import List

import pytest

from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
    file_to_native_image_config,
)


@pytest.fixture
def native_image_config(repo) -> NativeImageConfig:
    return file_to_native_image_config(repo.docker_native_image_config.path)


def test_load_native_image_config(native_image_config):
    """
    Given
    - native image configuration file

    When
    - loading its data

    Then
    - ensure data from the native image configuration file gets loaded properly
    """
    assert native_image_config.native_images
    assert native_image_config.ignored_content_items
    assert native_image_config.docker_images_to_native_images_mapping


def test_docker_images_to_supported_native_images(native_image_config):
    """
    Given
    - native image configuration file

    When
    - mapping docker images into native images

    Then
    - make sure each docker image is getting mapped correctly
    """
    assert native_image_config.docker_images_to_native_images_mapping == {
        "python3": ["native:8.1", "native:8.2", "native:dev"],
        "py3-tools": ["native:8.1", "native:8.2", "native:dev"],
        "unzip": ["native:8.1", "native:8.2", "native:dev"],
        "chromium": ["native:8.1", "native:8.2", "native:dev"],
        "tesseract": ["native:8.1", "native:8.2", "native:dev"],
        "pan-os-python": ["native:8.2"],
        "tld": ["native:8.1", "native:dev"],
    }


@pytest.mark.parametrize(
    "native_image, expected_image_reference",
    [("native:8.1", "demisto/py3-native:8.1.0.12345"), ("native:8.4", None)],
)
def test_get_native_image_reference(
    native_image_config, native_image, expected_image_reference
):
    """
    Given
    - native image configuration file, native image name:
        1. A native image that exists in the configuration file
        2. A native image that doesn't exist in the configuration file

    When
    - running the get_native_image_reference() function

    Then
    - make sure the right docker references is extracted
        1. The matched reference from the configuration file
        2. None
    """
    assert (
        native_image_config.get_native_image_reference(native_image)
        == expected_image_reference
    )


class TestScriptIntegrationSupportedNativeImages:
    @pytest.mark.parametrize(
        "_id, docker_image, expected_native_images",
        [
            (
                "UnzipFile",
                "demisto/unzip:1.0.0.23423",
                ["8.2"],
            ),
            ("Panorama", "demisto/pan-os-python:1.0.0.30307", []),
            ("Image OCR", "demisto/tesseract:1.0.0.36078", []),
            (
                "Prisma Cloud Compute",
                "demisto/python3:3.10.1.25933",
                ["8.1", "8.2"],
            ),
            ("SSDeepSimilarity", "demisto/ssdeep:1.0.0.23743", []),
        ],
    )
    def test_get_supported_native_image_versions(
        self,
        native_image_config,
        _id: str,
        docker_image: str,
        expected_native_images: List[str],
    ):
        """
        Given
        - Case A: a script that its docker-image is supported in 8.1 and 8.2, but should be ignored in 8.1.
        - Case B: an integration that its docker-image is supported only in 8.2, but should also be ignored in 8.2
        - Case C: an integration that its docker-image is supported in 8.1 and 8.2, but should be ignored in both.
        - Case D: an integration that its docker image is supported in 8.1 and 8.2 and should not be ignored.
        - Case E: an integration that its docker image is not supported in any native image.

        When
        - getting the supported native images

        Then
        - make sure each docker image is getting mapped correctly
            to the native images based also on the ignore mechanism
        """
        native_image_supported_versions = ScriptIntegrationSupportedNativeImages(
            _id=_id, docker_image=docker_image, native_image_config=native_image_config
        )

        assert (
            native_image_supported_versions.get_supported_native_image_versions(
                get_raw_version=True
            )
            == expected_native_images
        )

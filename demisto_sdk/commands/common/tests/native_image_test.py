from typing import List

import pytest

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.native_image import NativeImageConfig, NativeImageSupportedVersions

GIT_ROOT = git_path()
NATIVE_IMAGE_TEST_CONFIG_PATH = f'{GIT_ROOT}/demisto_sdk/commands/common/tests/test_files/native_image_config.json'


@pytest.fixture
def native_image_config() -> NativeImageConfig:
    return NativeImageConfig(NATIVE_IMAGE_TEST_CONFIG_PATH)


def test_load_native_image_config(native_image_config: NativeImageConfig):
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


def test_docker_images_to_supported_native_images(native_image_config: NativeImageConfig):
    """
    Given
    - native image configuration file

    When
    - mapping docker images into native images

    Then
    - make sure each docker image is getting mapped correctly
    """
    from demisto_sdk.commands.common.native_image import docker_images_to_native_images_support

    assert docker_images_to_native_images_support(native_image_config.native_images) == {
        'python3': ['8.1', '8.2'],
        'py3-tools': ['8.1', '8.2'],
        'unzip': ['8.1', '8.2'],
        'chromium': ['8.1', '8.2'],
        'tesseract': ['8.1', '8.2'],
        'pan-os-python': ['8.2'],
        'tld': ['8.1']
    }


class TestNativeImageSupportedVersions:

    @pytest.mark.parametrize(
        '_id, docker_image, expected_native_images',
        [
            (
                'Image OCR', 'demisto/tesseract:1.0.0.36078', ['8.1', '8.2'],
            ),
            (
                'Panorama', 'demisto/pan-os-python:1.0.0.30307', ['8.2']
            ),
            (
                'Prisma Cloud Compute', 'demisto/python3:3.10.1.25933', ['8.1', '8.2'],
            )
        ]
    )
    def test_image_to_native_images_support(
        self, native_image_config: NativeImageConfig, _id: str, docker_image: str, expected_native_images: List[str]
    ):
        """
        Given
        - native image configuration file
        - id of an integration
        - docker image of an integration

        When
        - mapping docker images into native images

        Then
        - make sure each docker image is getting mapped correctly to the native image that it supports
        """
        native_image_supported_versions = NativeImageSupportedVersions(
            _id=_id, docker_image=docker_image, native_image_config=native_image_config
        )
        assert native_image_supported_versions.image_to_native_images_support() == expected_native_images

    @pytest.mark.parametrize(
        '_id, docker_image, expected_native_images_to_ignore',
        [
            (
                'UnzipFile', 'demisto/unzip:1.0.0.23423', ['8.1'],
            ),
            (
                'Panorama', 'demisto/pan-os-python:1.0.0.30307', ['8.2'],
            ),
            (
                'Image OCR', 'demisto/tesseract:1.0.0.36078', ['8.1', '8.2'],
            ),
            (
                'Prisma Cloud Compute', 'demisto/python3:3.10.1.25933', []
            )
        ]
    )
    def test_get_ignored_native_images(
        self,
        native_image_config: NativeImageConfig,
        _id: str,
        docker_image: str,
        expected_native_images_to_ignore: List[str]
    ):
        """
        Given
        - native image configuration file
        - id of an integration
        - docker image of an integration

        When
        - getting the ignored images

        Then
        - make sure each docker image is getting mapped correctly to the native images which he should ignore
        """
        native_image_supported_versions = NativeImageSupportedVersions(
            _id=_id, docker_image=docker_image, native_image_config=native_image_config
        )

        assert native_image_supported_versions.get_ignored_native_images() == expected_native_images_to_ignore

    @pytest.mark.parametrize(
        '_id, docker_image, expected_native_images',
        [
            (
                'UnzipFile', 'demisto/unzip:1.0.0.23423', ['8.2'],
            ),
            (
                'Panorama', 'demisto/pan-os-python:1.0.0.30307', []
            ),
            (
                'Image OCR', 'demisto/tesseract:1.0.0.36078', []
            ),
            (
                'Prisma Cloud Compute', 'demisto/python3:3.10.1.25933', ['8.1', '8.2'],
            ),
            (
                'SSDeepSimilarity', 'demisto/ssdeep:1.0.0.23743', []
            ),
        ]
    )
    def test_get_supported_native_image_versions(
        self,
        native_image_config: NativeImageConfig,
        _id: str,
        docker_image: str,
        expected_native_images: List[str]
    ):
        """
        Given
        - Case A: a script that its docker-image is supported in 8.1 and 8.2, but should be ignored in 8.1.
        - Case B: an integration that its docker-image is supported only in 8.2, but should also be ignored in 8.2
        - Case C: an integration that its docker-image is supported in 8.1 and 8.2, but should be ignored in both.
        - Case D: an integration that its docker image is supported in 8.1 and 8.2 and should not be ignored.
        - Case E: an integration that its docker image is not supported in any native image.

        When
        - getting the ignored images

        Then
        - make sure each docker image is getting mapped correctly
            to the native images based also on the ignore mechanism
        """
        native_image_supported_versions = NativeImageSupportedVersions(
            _id=_id, docker_image=docker_image, native_image_config=native_image_config
        )

        assert native_image_supported_versions.get_supported_native_image_versions() == expected_native_images

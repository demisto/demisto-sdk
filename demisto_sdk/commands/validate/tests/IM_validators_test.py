import pytest
from pytest_mock import MockerFixture

from demisto_sdk.commands.common.constants import DEFAULT_IMAGE
from demisto_sdk.commands.content_graph.parsers.related_files import (
    ImageRelatedFile,
)
from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM100_image_exists_validation import (
    ImageExistsValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM101_image_too_large import (
    ImageTooLargeValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM106_default_image_validator import (
    DefaultImageValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM108_author_image_is_empty import (
    AuthorImageIsEmptyValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM109_author_image_exists_validation import (
    AuthorImageExistsValidator,
)
from demisto_sdk.commands.validate.validators.IM_validators.IM111_invalid_image_dimensions import (
    InvalidImageDimensionsValidator,
)


def test_ImageExistsValidator_obtain_invalid_content_items_image_path():
    """
    Given:
    content_items with 2 integrations:
        - One integration without image.
        - One integration with an existing image.

    When:
        - Calling the ImageExistsValidator obtain_invalid_content_items function.

    Then:
        - Make sure the right amount of integration image path failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
    """
    content_items = [create_integration_object(), create_integration_object()]
    content_items[0].image.exist = False
    results = ImageExistsValidator().obtain_invalid_content_items(content_items)
    assert len(results) == 1
    assert all(
        "You've created/modified a yml or package without providing an image as a .png file. Please make sure to add an image at TestIntegration_image.png."
        in result.message
        for result in results
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_integration_object(
                    paths=["image"], values=["data:image/png;base64,short image"]
                )
            ],
            0,
            [],
        ),
        (
            [
                create_integration_object(
                    paths=["image"],
                    values=["data:image/png;base64," + ("A very big image" * 1000)],
                )
            ],
            1,
            [
                "You've created/modified a yml or package with a large sized image. Please make sure to change the image dimensions at: TestIntegration_image.png."
            ],
        ),
    ],
)
def test_ImageTooLargeValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given:
    content_items:
        - Case 1: Integration with an image that is not in a valid size.
        - Case 2: Integration with an image that is in a valid size.

    When:
        - Calling the ImageTooLargeValidator obtain_invalid_content_items function.

    Then:
        - Make sure the right amount of integration image path failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
    """
    results = ImageTooLargeValidator().obtain_invalid_content_items(content_items)
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "image_resolution, expected_message",
    [
        ((120, 50), ""),
        (
            (1, 5),
            "The image dimensions do not match the requirements. A resolution of 120x50 pixels is required.",
        ),
        (
            (1200, 500),
            "The image dimensions do not match the requirements. A resolution of 120x50 pixels is required.",
        ),
    ],
)
def test_InvalidImageDimensionsValidator_obtain_invalid_content_items(
    mocker, image_resolution, expected_message
):
    mocker.patch(
        "demisto_sdk.commands.validate.validators.IM_validators.IM111_invalid_image_dimensions.imagesize.get",
        return_value=image_resolution,
    )
    content_items = [
        create_integration_object(paths=["image"], values=["very nice image"])
    ]

    results = InvalidImageDimensionsValidator().obtain_invalid_content_items(
        content_items
    )

    if len(results) > 0:
        assert results[0].message == expected_message


def test_AuthorImageExistsValidator_obtain_invalid_content_items_image_path():
    """
    Given:
    content_items (Pack).
        - Case 1: Author image path exists for community support pack.
        - Case 2: Author image path exists for partner support pack.
        - Case 3: Author image path doesn't exist for partner support pack.
        - Case 4: Author image path doesn't exist for community support pack.

    When:
        - Calling the AuthorImageExistsValidator obtain_invalid_content_items function.

    Then:
        - Make sure the right amount of pack author image path failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Shouldn't fail.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
    """
    content_items = [
        create_pack_object(paths=["support"], values=["community"]),
        create_pack_object(paths=["support"], values=["partner"]),
        create_pack_object(paths=["support"], values=["partner"]),
        create_pack_object(paths=["support"], values=["community"]),
    ]
    content_items[2].author_image_file.exist = False
    content_items[3].author_image_file.exist = False
    results = AuthorImageExistsValidator().obtain_invalid_content_items(content_items)
    assert len(results) == 1
    assert all(
        (
            "You've created/modified a partner supported pack without providing an author image as a .png file. Please "
            "make sure to add an image under the following path Packs/HelloWorld/Author_image.png"
        )
        in result.message
        for result in results
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        ([create_pack_object()], 0, []),
        (
            [create_pack_object(image="")],
            1,
            ["The author image should not be empty. Please provide a relevant image."],
        ),
    ],
)
def test_AuthorImageIsEmptyValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items.
        - Case 1: Author image not empty.
        - Case 2: Author image is empty.

    When
    - Calling the AuthorImageIsEmptyValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack author image failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
    """
    results = AuthorImageIsEmptyValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_DefaultImageValidator_obtain_invalid_content_items(mocker: MockerFixture):
    """
    Given:
        - First integration with a default image.
        - Second integration with a sample image

    When:
        - Calling the DefaultImageValidator obtain_invalid_content_items function.

    Then:
        - Make sure the right amount of integration image validation failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Shouldn't fail.
    """
    from pathlib import Path

    default_image = ImageRelatedFile(main_file_path=Path(DEFAULT_IMAGE))
    sample_image = ImageRelatedFile(
        main_file_path=Path("TestSuite/assets/default_integration/sample_image.png")
    )

    content_items = [create_integration_object(), create_integration_object()]
    mocker.patch.object(
        content_items[0].image, "load_image", return_value=default_image.load_image()
    )
    mocker.patch.object(
        content_items[1].image, "load_image", return_value=sample_image.load_image()
    )
    results = DefaultImageValidator().obtain_invalid_content_items(content_items)
    assert len(results) == 1
    assert (
        results[0].message
        == "The integration is using the default image at {0}, please change to the integration image.".format(
            DEFAULT_IMAGE
        )
    )

import pytest

from demisto_sdk.commands.common.tools import find_pack_folder
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_doc_file_object,
    create_integration_object,
    create_pack_object,
    create_playbook_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM101_is_image_path_valid import (
    IsImagePathValidValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM104_empty_readme import (
    EmptyReadmeValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM105_is_pack_readme_not_equal_pack_description import (
    IsPackReadmeNotEqualPackDescriptionValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM106_is_contain_demisto_word import (
    IsContainDemistoWordValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM107_is_template_sentence_in_readme import (
    IsTemplateInReadmeValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM108_is_integration_image_path_valid import (
    IntegrationRelativeImagePathValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM108_is_readme_image_path_valid import (
    ReadmeRelativeImagePathValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM109_is_readme_exists import (
    IsReadmeExistsValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM113_is_contain_copy_right_section import (
    IsContainCopyRightSectionValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM114_is_image_exists_in_readme import (
    IsImageExistsInReadmeValidator,
)
from TestSuite.repo import ChangeCWD


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_pack_object(readme_text="This is a valid readme."),
                create_pack_object(readme_text=""),
            ],
            0,
            [],
        ),
        (
            [create_pack_object(readme_text="Invalid readme\nBSD\nCopyright")],
            1,
            [
                "Invalid keywords related to Copyrights (BSD, MIT, Copyright, proprietary) were found in lines: 2, 3. Copyright section cannot be part of pack readme."
            ],
        ),
    ],
)
def test_IsContainCopyRightSectionValidator_obtain_invalid_content_items(
    content_items,
    expected_number_of_failures,
    expected_msgs,
):
    """
    Given
    content_items.
        - Case 1: Two valid pack_metadatas:
            - 1 pack with valid readme text.
            - 1 pack with an empty readme.
        - Case 2: One invalid pack_metadata with 2 lines contain copyright words
    When
    - Calling the IsContainCopyRightSectionValidator obtain_invalid_content_items function.
    Then
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Should pass all.
        - Case 3: Should fail.
    """
    results = IsContainCopyRightSectionValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_pack_object(
                    paths=["support"],
                    values=["partner"],
                    readme_text="This is a valid readme.",
                ),  # valid readme with partner support
                create_pack_object(
                    readme_text=""
                ),  # empty readme but with no partner support and no playbooks
                create_pack_object(
                    readme_text="This is valid readme", playbooks=1
                ),  # should pass as it has a valid readme and playbooks
            ],
            0,
            [],
        ),
        (
            [
                create_pack_object(
                    paths=["support"], values=["partner"], readme_text=""
                ),
            ],  # empty readme with partner support, not valid
            1,
            [
                "Pack HelloWorld written by a partner or pack containing playbooks must have a full README.md file with pack information. Please refer to https://xsoar.pan.dev/docs/documentation/pack-docs#pack-readme for more information",
            ],
        ),
        (
            [
                create_pack_object(readme_text="", playbooks=1)
            ],  # empty readme with playbooks, not valid
            1,
            [
                "Pack HelloWorld written by a partner or pack containing playbooks must have a full README.md file with pack information. Please refer to https://xsoar.pan.dev/docs/documentation/pack-docs#pack-readme for more information"
            ],
        ),
    ],
)
def test_empty_readme_validator(
    content_items,
    expected_number_of_failures,
    expected_msgs,
):
    """
    Given:
    - content_items.
        - Case 1: Three valid pack_metadatas:
            - 1 pack with valid readme text and partner support.
            - 1 pack with an empty readme.
            - 1 pack with valid readme and playbooks.
        - Case 2: One invalid pack_metadata with empty readme and partner support.
        - Case 3: One invalid pack_metadata with empty readme and playbooks.

    When:
    - Calling the EmptyReadmeValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
    """

    results = EmptyReadmeValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        ([create_integration_object()], 0),
        (
            [
                create_integration_object(
                    readme_content='<img src="https://github.com/demisto/content/blob/path/to/image.jpg" alt="Alt text">'
                )
            ],
            1,
        ),
        (
            [
                create_script_object(
                    readme_content='<img src="https://github.com/demisto/content/blob/path/to/image.jpg" alt="Alt text">'
                )
            ],
            1,
        ),
        (
            [
                create_pack_object(
                    readme_text='<img src="https://github.com/demisto/content/blob/path/to/image.jpg" alt="Alt text">'
                )
            ],
            1,
        ),
        (
            [
                create_playbook_object(
                    readme_content='<img src="https://github.com/demisto/content/blob/path/to/image.jpg" alt="Alt text">'
                )
            ],
            1,
        ),
    ],
)
def test_is_image_path_validator(content_items, expected_number_of_failures):
    """
    Given:
        - A list of content items with their respective readme contents.
    When:
        - The IsImagePathValidValidator is run on the provided content items.
            - A content item with no images (expected failures: 0).
            - A content item with a non-raw image URL in the readme (expected failures: 1).
            - A script object with a non-raw image URL in the readme (expected failures: 1).
            - A pack object with a non-raw image URL in the readme (expected failures: 1).
            - A playbook object with a non-raw image URL in the readme (expected failures: 1).

    Then:
        - Validate that the number of detected invalid image paths matches the expected number of failures.
        - Ensure that each failure message correctly identifies the non-raw GitHub image URL and suggests the proper raw URL format.
    """
    results = IsImagePathValidValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message.endswith(
                "detected the following images URLs which are not raw links: https://github.com/demisto/content/blob/path/to/image.jpg suggested URL https://github.com/demisto/content/raw/path/to/image.jpg"
            )
            for result in results
        ]
    )


@pytest.mark.parametrize(
    "content_items, is_file_exist, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_playbook_object(
                    readme_content="This is a valid readme without any images.",
                    pack_info={"name": "test1"},
                ),
                create_playbook_object(
                    readme_content="This is a valid readme if this file exists ![example image](../doc_files/example.png)",
                    pack_info={"name": "test1"},
                ),
                create_playbook_object(readme_content="", pack_info={"name": "test1"}),
                create_integration_object(
                    readme_content="This is a valid readme without any images.",
                    pack_info={"name": "test2"},
                ),
                create_integration_object(
                    readme_content="This is a valid readme if this file exists ![example image](../doc_files/example.png)",
                    pack_info={"name": "test2"},
                ),
                create_integration_object(
                    readme_content="This is a valid readme if this file exists ![example image](../doc_files/example.jpg)",
                    pack_info={"name": "test2"},
                ),
                create_integration_object(
                    readme_content="", pack_info={"name": "test2"}
                ),
            ],
            [None, "example.png", None, None, "example.png", "example.jpg", None],
            0,
            [],
        ),
        (
            [
                create_playbook_object(
                    readme_content="This is not a valid readme if this file doesn't exists ![example image](../doc_files/example.png), ",
                    pack_info={"name": "test1"},
                ),
                create_integration_object(
                    readme_content="This is not a valid readme if this file doesn't exists ![example image](../doc_files/example.png)",
                    pack_info={"name": "test2"},
                ),
                create_playbook_object(
                    readme_content="This is not a valid readme if this file doesn't exists ![example image](../doc_files/example.png ), ",
                    pack_info={"name": "test3"},
                ),
                create_integration_object(
                    readme_content="This is not a valid readme if this file doesn't exists ![example image]( ../doc_files/example.png)",
                    pack_info={"name": "test4"},
                ),
                create_integration_object(
                    readme_content="This is not a valid readme if this file doesn't exists ![example image](../doc_files/example.jpg)",
                    pack_info={"name": "test5"},
                ),
            ],
            [None, None, "example.png", "example.png", None],
            5,
            [
                "The following images do not exist: Packs/test1/doc_files/example.png",
                "The following images do not exist: Packs/test2/doc_files/example.png",
                "The following images do not exist: Packs/test3/doc_files/example.png",
                "The following images do not exist: Packs/test5/doc_files/example.jpg",
            ],
        ),
    ],
)
def test_IsImageExistsInReadmeValidator_obtain_invalid_content_items(
    content_items,
    is_file_exist,
    expected_number_of_failures,
    expected_msgs,
):
    with ChangeCWD(REPO.path):
        for content_item, file_name in zip(content_items, is_file_exist):
            if file_name:
                create_doc_file_object(find_pack_folder(content_item.path), file_name)

        results = IsImageExistsInReadmeValidator().obtain_invalid_content_items(
            content_items
        )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            (result.message, expected_msg)
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsPackReadmeNotEqualPackDescriptionValidator_not_valid():
    """
    Given:
        - Pack with a readme pack equal to the description
    When:
        - run IsPackReadmeNotEqualPackDescriptionValidator obtain_invalid_content_items function
    Then:
        - Ensure that the error msg returned is as expected
    """

    content_items = [
        create_pack_object(
            readme_text="This readme text and pack_metadata description are equal",
            paths=["description"],
            values=["This readme text and pack_metadata description are equal"],
        )
    ]
    assert IsPackReadmeNotEqualPackDescriptionValidator().obtain_invalid_content_items(
        content_items
    )


def test_IsPackReadmeNotEqualPackDescriptionValidator_valid():
    """
    Given:
        - Pack with different readme and description
    When:
        - run obtain_invalid_content_items method
    Then:
        - Ensure that no ValidationResult returned
    """
    content_items = [
        create_pack_object(
            readme_text="Readme text",
            paths=["description"],
            values=["Pack_metadata description"],
        ),
    ]
    assert (
        not IsPackReadmeNotEqualPackDescriptionValidator().obtain_invalid_content_items(
            content_items
        )
    )


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_playbook_object(),
                create_playbook_object(),
            ],
            1,
            [
                "The Playbook 'Detonate File - JoeSecurity V2' doesn't have a README file. Please add a README.md file in the content item's directory."
            ],
        ),
        (
            [
                create_script_object(),
                create_script_object(),
            ],
            1,
            [
                "The Script 'myScript' doesn't have a README file. Please add a README.md file in the content item's directory."
            ],
        ),
        (
            [
                create_integration_object(),
                create_integration_object(),
            ],
            1,
            [
                "The Integration 'TestIntegration' doesn't have a README file. Please add a README.md file in the content item's directory."
            ],
        ),
    ],
)
def test_IsReadmeExistsValidator_obtain_invalid_content_items(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given:
        - Integration, Script and Playbook objects- one have and one does not have README file
    When:
        - run obtain_invalid_content_items method from IsReadmeExistsValidator
    Then:
        - Ensure that for each test only one ValidationResult returns with the correct message
    """
    content_items[1].readme.exist = False
    results = IsReadmeExistsValidator().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsContainDemistoWordValidator_obtain_invalid_content_items():
    """
    Given
    content_items.
        - Two valid pack_metadatas:
            - 1 pack with valid readme text.
            - 1 pack with an empty readme.    When
    - Calling the IsContainDemistoWordValidator obtain_invalid_content_items function.
    Then
        - Make sure that the pack isn't failing.
        - Should pass all.
    """
    content_items = [
        create_pack_object(readme_text="This is a valid readme."),
        create_pack_object(readme_text=""),
    ]
    results = IsContainDemistoWordValidator().obtain_invalid_content_items(
        content_items
    )
    expected_msg = []
    assert len(results) == 0
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msg)
        ]
    )


def test_IsContainDemistoWordValidator_is_invalid():
    """
    Given
    content_items.
        - One invalid pack_metadata with a readme that contains the word 'demisto'.
    When
    - Calling the IsContainDemistoWordValidator obtain_invalid_content_items function.
    Then
    - Make sure the right amount of pack failed, and that the right error message is returned.
    """
    content_items = [
        create_pack_object(
            readme_text="Invalid readme contains the word demistomock\ndemisto \ndemisto \ndemisto.\n mockdemisto."
        )
    ]
    expected_msg = "Invalid keyword 'demisto' was found in lines: 1, 2, 3, 4, 5. For more information about the README See https://xsoar.pan.dev/docs/documentation/readme_file."
    results = IsContainDemistoWordValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == 1
    assert results[0].message == expected_msg


def test_ImagePathIntegrationValidator_obtain_invalid_content_items_valid_case():
    """
    Given
    content_items.
    - Pack with valid readme and valid description contain only relative paths.
    When
    - Calling the ImagePathIntegrationValidator obtain_invalid_content_items function.
    Then
    - Make sure that the pack isn't failing.
    """
    content_items = [
        create_integration_object(
            readme_content="![Example Image](../doc_files/image.png)",
            description_content="valid description ![Example Image](../doc_files/image.png)",
        ),
    ]
    assert not IntegrationRelativeImagePathValidator().obtain_invalid_content_items(
        content_items
    )


def test_ImagePathIntegrationValidator_obtain_invalid_content_items_invalid_case():
    """
        Given
        content_items.
        - Pack with:
            1. invalid readme that contains absolute path.
            2. description contains relative path that saved not under dec_files.
    demisto_sdk/commands/validate/sdk_validation_config.toml

        When
        - Calling the ImagePathIntegrationValidator obtain_invalid_content_items function.
        Then
        - Make sure that the pack is failing.
    """
    content_items = [
        create_integration_object(
            readme_content=" Readme contains absolute path:\n 'Here is an image:\n"
            " ![Example Image](https://www.example.com/images/example_image.jpg)",
            description_content="valid description ![Example Image](../../content/image.jpg)",
        ),
    ]
    expected = (
        " Invalid image path(s) have been detected. Please utilize relative paths instead for the links "
        "provided below.:\nhttps://www.example.com/images/example_image.jpg\n\nRelative image paths have been"
        " identified outside the pack's 'doc_files' directory. Please relocate the following images to the"
        " 'doc_files' directory:\n../../content/image.jpg\n\n Read the following documentation on how to add"
        " images to pack markdown files:\n https://xsoar.pan.dev/docs/integrations/integration-docs#images"
    )
    result = IntegrationRelativeImagePathValidator().obtain_invalid_content_items(
        content_items
    )
    assert result[0].message == expected


def test_ImagePathOnlyReadMeValidator_obtain_invalid_content_items_valid_case():
    """
    Given
    content_items.
    - Pack with valid readme contains only relative paths.
    When
    - Calling the ImagePathIntegrationValidator obtain_invalid_content_items function.
    Then
    - Make sure that the pack isn't failing.
    """
    content_items = [
        create_integration_object(
            readme_content="![Example Image](../doc_files/image.png)",
        ),
    ]
    assert not ReadmeRelativeImagePathValidator().obtain_invalid_content_items(
        content_items
    )


def test_ImagePathOnlyReadMeValidator_obtain_invalid_content_items_invalid_case():
    """
    Given
    content_items.
    - Pack with:
        1. invalid readme that contains absolute path and contains
         relative path that saved not under dec_files.

    When
    - Calling the ImagePathOnlyReadMeValidator obtain_invalid_content_items function.

    Then
    - Make sure that the pack is failing.
    """
    content_items = [
        create_integration_object(
            readme_content=" Readme contains absolute path:\n 'Here is an image:\n"
            " ![Example Image](https://www.example.com/images/example_image.jpg)"
            " ![Example Image](../../content/image.jpg)",
        ),
    ]
    expected = (
        " Invalid image path(s) have been detected. Please utilize relative paths instead for the links"
        " provided below.:\nhttps://www.example.com/images/example_image.jpg\n\nRelative image paths have been"
        " identified outside the pack's 'doc_files' directory. Please relocate the following images to the"
        " 'doc_files' directory:\n../../content/image.jpg\n\n Read the following documentation on how to add"
        " images to pack markdown files:\n https://xsoar.pan.dev/docs/integrations/integration-docs#images"
    )

    result = ReadmeRelativeImagePathValidator().obtain_invalid_content_items(
        content_items
    )
    assert result[0].message == expected


def test_VerifyTemplateInReadmeValidator_valid_case(repo):
    """
    Given
    content_items.
    - Integration with readme that contains %%FILL HERE%% template substring.
    - Script with readme that contains %%FILL HERE%% template substring.
    - Playbook with readme that contains %%FILL HERE%% template substring.
    - Pack with readme that contains %%FILL HERE%% template substring.
    When
    - Calling the IsTemplateInReadmeValidator obtain_invalid_content_items function.

    Then
    - Make sure that the validator return the list of the content items, which has %%FILL HERE%% in the readme file.
    """
    content_items = [
        create_integration_object(
            readme_content="This checks if we have the sentence %%FILL HERE%% in the README.",
        ),
        create_script_object(
            readme_content="This checks if we have the sentence %%FILL HERE%% in the README.",
        ),
        create_playbook_object(
            readme_content="This checks if we have the sentence %%FILL HERE%% in the README.",
        ),
        create_pack_object(
            readme_text="This checks if we have the sentence %%FILL HERE%% in the README.",
        ),
    ]

    expected_error_message = "The template '%%FILL HERE%%' exists in the following lines of the README content: 1."
    validator_results = IsTemplateInReadmeValidator().obtain_invalid_content_items(
        content_items
    )
    assert validator_results
    for validator_result in validator_results:
        assert validator_result.message == expected_error_message


def test_VerifyTemplateInReadmeValidator_invalid_case(repo):
    """
    Given
    content_items.
    - Integration with readme without %%FILL HERE%% template substring.
    - Script with readme without %%FILL HERE%% template substring.
    - Playbook with readme without %%FILL HERE%% template substring.
    - Pack with readme without %%FILL HERE%% template substring.
    When
    - Calling the IsTemplateInReadmeValidator obtain_invalid_content_items function.

    Then
    - Make sure that the validator return empty list.
    """
    content_items = [
        create_integration_object(
            readme_content="The specific template substring is not in the README.",
        ),
        create_script_object(
            readme_content="The specific template substring is not in the README.",
        ),
        create_playbook_object(
            readme_content="The specific template substring is not in the README.",
        ),
        create_pack_object(
            readme_text="The specific template substring is not in the README.",
        ),
    ]
    assert not IsTemplateInReadmeValidator().obtain_invalid_content_items(content_items)

from pathlib import PosixPath

import more_itertools
import pytest
from click.exceptions import BadParameter

from demisto_sdk.commands.common.tools import find_pack_folder
from demisto_sdk.commands.validate.tests.test_tools import (
    REPO,
    create_doc_file_object,
    create_integration_object,
    create_pack_object,
    create_playbook_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult
from demisto_sdk.commands.validate.validators.RM_validators.RM100_no_empty_sections import (
    EmptySectionsValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM101_is_image_path_valid import (
    IsImagePathValidValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM102_is_missing_context_output import (
    IsMissingContextOutputValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM103_is_using_brands_section_exists import (
    IsUsingBrandsSectionExistsValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM104_empty_readme import (
    EmptyReadmeValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM105_is_pack_readme_not_equal_pack_description import (
    IsPackReadmeNotEqualPackDescriptionValidator,
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
from demisto_sdk.commands.validate.validators.RM_validators.RM110_is_commands_in_readme import (
    IsCommandsInReadmeValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM113_is_contain_copy_right_section import (
    IsContainCopyRightSectionValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM114_is_image_exists_in_readme import (
    IsImageExistsInReadmeValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM115_no_default_section_left import (
    NoDefaultSectionsLeftReadmeValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM116_missing_playbook_image import (
    MissingPlaybookImageValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM117_readme_not_to_short import (
    NotToShortReadmeValidator,
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
                "Detected the following images URLs which are not raw links: https://github.com/demisto/content/blob/path/to/image.jpg suggested URL https://github.com/demisto/content/raw/path/to/image.jpg"
            )
            for result in results
        ]
    )


@pytest.mark.parametrize(
    "content_items, doc_files_name, expected_number_of_failures, expected_msgs",
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
                "The following images do not exist or have additional characters present in their declaration within the README: Packs/test1/doc_files/example.png",
                "The following images do not exist or have additional characters present in their declaration within the README: Packs/test2/doc_files/example.png",
                "The following images do not exist or have additional characters present in their declaration within the README: Packs/test3/doc_files/example.png",
                "The following images do not exist or have additional characters present in their declaration within the README: Packs/test5/doc_files/example.jpg",
            ],
        ),
    ],
)
def test_IsImageExistsInReadmeValidator_obtain_invalid_content_items(
    content_items,
    doc_files_name,
    expected_number_of_failures,
    expected_msgs,
):
    with ChangeCWD(REPO.path):
        for content_item, file_name in zip(content_items, doc_files_name):
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


def test_IsImageExistsInReadmeValidator_invalid_image_paths(mocker):
    """
    Given:
        - A pack name and a list of image paths, some with a missing prefix and others already valid.
    When:
        - Running the `get_invalid_image_paths` function to validate image paths.
    Then:
        - Ensure that initially invalid paths are identified.
        - Ensure that removing the prefix allows paths to be validated successfully.
    """
    import click

    pack_name = "MyPack"
    image_paths = [
        "../doc_files/valid_image.png",  # Will be valid after adding prefix
    ]

    # Mocking click.Path.convert to simulate file validation
    def mock_first_convert(path, param, ctx):
        # Simulate failed validation for all paths during second call
        raise BadParameter

    def mock_second_convert(path, param, ctx):
        # Simulate successful validation for all paths during second call
        pass

    mocker.patch.object(
        click.Path, "convert", side_effect=[mock_first_convert, mock_second_convert]
    )
    invalid_paths = IsImageExistsInReadmeValidator.get_invalid_image_paths(
        pack_name, image_paths
    )
    assert not invalid_paths


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
        - Make sure that two different errors are thrown, one for each related file and that the error message is as expected.
    """
    content_items = [
        create_integration_object(
            readme_content=" Readme contains absolute path:\n 'Here is an image:\n"
            " ![Example Image](https://www.example.com/images/example_image.jpg)",
            description_content="valid description ![Example Image](../../content/image.jpg)",
        ),
    ]
    expected_msgs = (
        " Invalid image path(s) have been detected. Please utilize relative paths instead for the links provided below:\nhttps://www.example.com/images/example_image.jpg\n\n Read the following documentation on how to add images to pack markdown files:\n https://xsoar.pan.dev/docs/integrations/integration-docs#images",
        "Relative image paths have been identified outside the pack's 'doc_files' directory. Please relocate the following images to the 'doc_files' directory:\n../../content/image.jpg\n\n Read the following documentation on how to add images to pack markdown files:\n https://xsoar.pan.dev/docs/integrations/integration-docs#images",
    )
    results = IntegrationRelativeImagePathValidator().obtain_invalid_content_items(
        content_items
    )

    assert len(results) == 2
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


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
        " provided below:\nhttps://www.example.com/images/example_image.jpg\n\nRelative image paths have been"
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


def test_get_command_context_path_from_readme_file_missing_from_yml():
    """
    Given a command name and README content, and missing commands from yml
    When get_command_context_path_from_readme_file is called
    Then it should return the expected set of context paths
    """
    readme_content = (
        "### test-command\n"
        "***\n"
        "test.\n\n\n"
        "#### Base Command\n\n"
        "`test-command`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description**                  | **Required** |\n"
        "| ----------------- | -------------------------------- | ------------ |\n"
        "| short_description | Short description of the ticket. | Optional     |\n\n\n"
        " #### Context Output\n\n"
        "| **Path**             | **Type** | **Description**       |\n"
        "| -------------------- | -------- | --------------------- |\n"
        "| Test.Path1 | string   | test. |\n"
    )
    integrations = [
        create_integration_object(
            paths=[
                "script.commands",
            ],
            values=[[{"name": "test-command"}]],
            readme_content=readme_content,
        ),
    ]
    results = IsMissingContextOutputValidator().obtain_invalid_content_items(
        integrations
    )
    assert (
        results[0].message
        == "Find discrepancy for the following commands:\ntest-command:\nThe following outputs are missing from yml: Test.Path1\n"
    )


def test_get_command_context_path_from_readme_file_missing_from_readme():
    """
    Given a command name and README content with missing context outputs
    When get_command_context_path_from_readme_file is called
    Then it should return the expected set of context paths and show missing from readme
    """
    readme_content = (
        "### test-command\n"
        "***\n"
        "test.\n\n\n"
        "#### Base Command\n\n"
        "`test-command`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description** | **Required** |\n"
        "| ----------------- | --------------- | ------------ |\n"
        "| arg1              | Test argument   | Optional     |\n\n\n"
        " #### Context Output\n\n"
        "| **Path**    | **Type** | **Description** |\n"
        "| ----------- | -------- | --------------- |\n"
        "| Test.Path1  | string   | test.           |\n"
    )
    yml_content = {
        "script": {
            "commands": [
                {
                    "name": "test-command",
                    "outputs": [
                        {"contextPath": "Test.Path1"},
                        {"contextPath": "Test.Path2"},
                    ],
                }
            ]
        }
    }
    content_item = create_integration_object(
        paths=["script.commands"],
        values=[yml_content["script"]["commands"]],
        readme_content=readme_content,
    )
    results = IsMissingContextOutputValidator().obtain_invalid_content_items(
        [content_item]
    )
    assert (
        results[0].message
        == "Find discrepancy for the following commands:\ntest-command:\nThe following outputs are missing from readme: Test.Path2\n"
    )


def test_get_command_context_path_from_readme_file_no_discrepancies():
    """
    Given a command name and README content with matching context outputs in YML
    When get_command_context_path_from_readme_file is called
    Then it should return an empty list of results
    """
    readme_content = (
        "### test-command\n"
        "***\n"
        "test.\n\n\n"
        "#### Base Command\n\n"
        "`test-command`\n"
        "#### Input\n\n"
        "| **Argument Name** | **Description** | **Required** |\n"
        "| ----------------- | --------------- | ------------ |\n"
        "| arg1              | Test argument   | Optional     |\n\n\n"
        " #### Context Output\n\n"
        "| **Path**    | **Type** | **Description** |\n"
        "| ----------- | -------- | --------------- |\n"
        "| Test.Path1  | string   | test.           |\n"
        "| Test.Path2  | string   | test.           |\n"
    )
    yml_content = {
        "script": {
            "commands": [
                {
                    "name": "test-command",
                    "outputs": [
                        {"contextPath": "Test.Path1"},
                        {"contextPath": "Test.Path2"},
                    ],
                }
            ]
        }
    }
    content_item = create_integration_object(
        paths=["script.commands"],
        values=[yml_content["script"]["commands"]],
        readme_content=readme_content,
    )
    results = IsMissingContextOutputValidator().obtain_invalid_content_items(
        [content_item]
    )
    assert len(results) == 0


def test_get_command_context_path_from_readme_file_multiple_commands():
    """
    Given multiple commands with discrepancies in context outputs
    When get_command_context_path_from_readme_file is called
    Then it should return the expected set of context paths for all commands
    """
    readme_content = (
        "### command1\n"
        "***\n"
        "test.\n\n\n"
        "#### Base Command\n\n"
        "`command1`\n"
        "#### Context Output\n\n"
        "| **Path**    | **Type** | **Description** |\n"
        "| ----------- | -------- | --------------- |\n"
        "| Test.Path1  | string   | test.           |\n"
        "### command2\n"
        "***\n"
        "test.\n\n\n"
        "#### Base Command\n\n"
        "`command2`\n"
        "#### Context Output\n\n"
        "| **Path**    | **Type** | **Description** |\n"
        "| ----------- | -------- | --------------- |\n"
        "| Test.Path2  | string   | test.           |\n"
        "| Test.Path3  | string   | test.           |\n"
    )
    yml_content = {
        "script": {
            "commands": [
                {
                    "name": "command1",
                    "outputs": [
                        {"contextPath": "Test.Path1"},
                        {"contextPath": "Test.Path2"},
                    ],
                },
                {
                    "name": "command2",
                    "outputs": [
                        {"contextPath": "Test.Path2"},
                        {"contextPath": "Test.Path4"},
                    ],
                },
            ]
        }
    }
    content_item = create_integration_object(
        paths=["script.commands"],
        values=[yml_content["script"]["commands"]],
        readme_content=readme_content,
    )
    results = IsMissingContextOutputValidator().obtain_invalid_content_items(
        [content_item]
    )
    assert len(results) == 1
    assert (
        "command1:\nThe following outputs are missing from readme: Test.Path2\n"
        in results[0].message
    )
    assert (
        "command2:\nThe following outputs are missing from yml: Test.Path3\nThe following outputs are missing from readme: Test.Path4\n"
        in results[0].message
    )


def test_IsCommandsInReadmeValidator_not_valid():
    """
    Given: An integration object with commands 'command1' and 'command2'
    When: The README content is empty
    Then: The IsCommandsInReadmeValidator should return a single result with a message
          indicating that the commands are missing from the README file
    """
    content_item = create_integration_object(
        paths=["script.commands"],
        values=[
            [
                {"name": "command1"},
                {"name": "command2"},
            ]
        ],
        readme_content="",
    )
    results = IsCommandsInReadmeValidator().obtain_invalid_content_items([content_item])
    assert more_itertools.one(results), "The validator should return a single result"
    assert results[0].message == (
        "The following commands appear in the YML file but not in the README file: command1, command2."
    )


def test_IsCommandsInReadmeValidator_valid():
    """
    Given: An integration object with commands 'command1' and 'command2'
    When: The README content includes both command names
    Then: The IsCommandsInReadmeValidator should not report any invalid content items
    """
    content_item = create_integration_object(
        paths=["script.commands"],
        values=[
            [
                {"name": "command1"},
                {"name": "command2"},
            ]
        ],
        readme_content="command1, command2",
    )
    assert not IsCommandsInReadmeValidator().obtain_invalid_content_items(
        [content_item]
    )


def test_missing_playbook_image_validator_no_image():
    """
    Given
    content_items.
    - Playbook without an image
    When
    - Calling the MissingPlaybookImageValidator obtain_invalid_content_items function.

    Then
    - Make sure that the validator returns an error
    """
    content_items = [
        create_playbook_object(),
    ]
    result = MissingPlaybookImageValidator().obtain_invalid_content_items(content_items)
    assert len(result) == 1


def test_missing_playbook_image_validator_image_exists_wrong_path():
    """
    Given
    content_items.
    - Playbook with an image, but wrong path (the path doesn't include doc_files folder)
    When
    - Calling the MissingPlaybookImageValidator obtain_invalid_content_items function.

    Then
    - Make sure that the validator returns an error
    """
    content_items = [
        create_playbook_object(),
    ]
    content_items[0].image.exist = True
    result = MissingPlaybookImageValidator().obtain_invalid_content_items(content_items)
    assert len(result) == 1


def test_missing_playbook_image_validator_image_exists_with_path():
    """
    Given
    content_items.
    - Playbook with an image and correct path
    When
    - Calling the MissingPlaybookImageValidator obtain_invalid_content_items function.

    Then
    - Make sure that the validator returns an empty list
    """
    content_items = [
        create_playbook_object(),
    ]
    content_items[0].image.exist = True
    content_items[0].image.file_path = PosixPath(
        "/var/folders/sd/bk6skd0j1xz7l1g8d4dhfn7c0000gp/T/tmpjmydes4n/Packs/doc_files/Playbooks/playbook-0.png"
    )
    result = MissingPlaybookImageValidator().obtain_invalid_content_items(content_items)
    assert len(result) == 0


@pytest.mark.parametrize(
    "file_input, missing_section",
    [
        ("## Troubleshooting\n## OtherSection", "Troubleshooting"),
        ("## Troubleshooting", "Troubleshooting"),
        ("## Troubleshooting\n\n---\n## OtherSection", "Troubleshooting"),
        ("## Use Cases\n\n----------\n## OtherSection", "Use Cases"),
        ("## Additional Information\n\n## OtherSection", "Additional Information"),
        ("## Known Limitations\n\n----------\n", "Known Limitations"),
    ],
)
def test_unvalid_verify_no_empty_sections(file_input, missing_section):
    """
    Given
        - Empty sections in different forms
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    content_item = create_integration_object(readme_content=file_input)
    validation_result: list[ValidationResult] = (
        EmptySectionsValidator().obtain_invalid_content_items([content_item])
    )
    section_error = f"The section/s: {missing_section} is/are empty\nplease elaborate or delete the section.\n"
    if validation_result:
        assert validation_result[0].message == section_error


def test_combined_unvalid_verify_no_empty_sections():
    """
    Given
        - Couple of empty sections
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    file_input = "## Troubleshooting\n## OtherSection\n## Additional Information\n\n## OtherSection\n##"
    content_item = create_integration_object(readme_content=file_input)
    empty_section_validator = EmptySectionsValidator()
    validation_results: list[ValidationResult] = (
        empty_section_validator.obtain_invalid_content_items([content_item])
    )
    error = "The section/s: Troubleshooting, Additional Information is/are empty\nplease elaborate or delete the section.\n"
    assert error == validation_results[0].message


@pytest.mark.parametrize(
    "file_input",
    [
        "## Troubleshooting\ninput",
        "## Troubleshooting\n\n---\ninput",
        "## Use Cases\n\n----------\ninput",
        "## Additional Information\n\ninput",
        "## Additional Information\n\n### OtherSection",
        "## Known Limitations\n\n----------\ninput",
    ],
)
def test_valid_sections(file_input):
    """
    Given
        - Valid sections in different forms from SECTIONS
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    content_item = create_integration_object(readme_content=file_input)
    validation_result: list[ValidationResult] = (
        EmptySectionsValidator().obtain_invalid_content_items([content_item])
    )
    assert not validation_result


@pytest.mark.parametrize(
    "file_input, section",
    [
        (
            "##### Required Permissions\n**FILL IN REQUIRED PERMISSIONS HERE**\n##### Base Command",
            "FILL IN REQUIRED PERMISSIONS HERE",
        ),
        (
            "##### Required Permissions **FILL IN REQUIRED PERMISSIONS HERE**\n##### Base Command",
            "FILL IN REQUIRED PERMISSIONS HERE",
        ),
        (
            "##### Required Permissions FILL IN REQUIRED PERMISSIONS HERE",
            "FILL IN REQUIRED PERMISSIONS HERE",
        ),
        (
            "##### Required Permissions FILL IN REQUIRED PERMISSIONS HERE",
            "FILL IN REQUIRED PERMISSIONS HERE",
        ),
        (
            "This integration was integrated and tested with version xx of integration v2.",
            "version xx",
        ),
        (
            "##Dummy Integration\n this integration is for getting started and learn how to build an "
            "integration. some extra text here",
            "getting started and learn how to build an integration",
        ),
        (
            "In this readme template all required notes should be replaced.\n# %%UPDATE%% <Product Name>",
            "%%UPDATE%%",
        ),
    ],
)
def test_verify_no_default_sections_left(file_input, section):
    """
    Given
        - Readme that contains sections that are created as default and need to be changed
    When
        - Run validate on README file
    Then
        - Ensure no default sections in the readme file
    """
    content_item = create_integration_object(readme_content=file_input)
    no_default_section_left_validator = NoDefaultSectionsLeftReadmeValidator()
    validation_result: list[ValidationResult] = (
        no_default_section_left_validator.obtain_invalid_content_items([content_item])
    )
    section_error = f'The following default sentences "{section}" still exist in the readme, please replace with a suitable info.'
    assert section_error == validation_result[0].message


def test_readme_ignore():
    """
    Check that packs in ignore list are ignored.
       Given
            - A pack from the ignore list
        When
            - Run validate on README of ignored pack
        Then
            - Ensure validation ignored the pack
    """
    readme_text = "getting started and learn how to build an integration"
    pack_content_item = create_pack_object(name="HelloWorld", readme_text=readme_text)
    no_default_section_left_validator = NoDefaultSectionsLeftReadmeValidator()
    assert not no_default_section_left_validator.obtain_invalid_content_items(
        [pack_content_item]
    )


def test_invalid_short_file():
    """
    Given
        - Non empty Readme with less than 30 chars.
    When
        - Running validate on README file
    Then
        - Ensure verify on Readme fails
    """
    short_readme = "This is a short readme"
    test_pack = create_pack_object(readme_text=short_readme)
    not_to_short_readme_validator = NotToShortReadmeValidator()
    short_readme_error = """Your Pack README is too short (22 chars). Please move its content to the pack description or add more useful information to the Pack README. Pack README files are expected to include a few sentences about the pack and/or images."""

    result: list[ValidationResult] = (
        not_to_short_readme_validator.obtain_invalid_content_items([test_pack])
    )
    assert result[0].message == short_readme_error


def test_ImagePathIntegrationValidator_content_assets():
    """
    Given
    content_items.
    - Pack with:
        1. An invalid readme contains absolute path. For example:
            - https://www.example.com/content-assets/example_image.jpg
         2. An invalid readme contains a relative path not saved under doc_files. For example:
            - img_docs/58381182-d8408200-7fc2-11e9-8726-8056cab1feea.png
        3. An invalid readme contains absolute gif path not under content-assets. For example:
            - https://www.example.com/example_image.gif
        4. A valid readme contains absolute gif path under content-assets. For example:
            - https://www.example.com/example_image.gif
        4. A valid readme contains relative path saved under doc_files. For example:
            - ../../doc_files/58381182-d8408200-7fc2-11e9-8726-8056cab1feea.png

    When
    - Calling the ImagePathIntegrationValidator obtain_invalid_content_items function.
    Then
    - Make sure that the pack is failing.
    """
    content_items = [
        create_integration_object(
            readme_content=" Readme contains absolute path:\n 'Here is an image:\n"
            " ![Example Image](https://www.example.com/images/example_image.jpg)\n"
            "![Example Image](https://www.example.com/content-assets/example_image.jpg)\n"
            "<img src='../../doc_files/58381182-d8408200-7fc2-11e9-8726-8056cab1feea.png'\n"
            "<img src='../Playbooks/58381182-d8408200-7fc2-11e9-8726-8056cab1feea.png'\n"
            "![Example Image](https://www.example.com/content-assets/example_image.gif)\n"
            "![Example Image](https://www.example.com/example_image.gif)\n",
        ),
    ]
    expected = (
        " Invalid image path(s) have been detected. Please utilize relative paths instead for the links "
        "provided below:\nhttps://www.example.com/images/example_image.jpg\n"
        "https://www.example.com/content-assets/example_image.jpg\n"
        "https://www.example.com/example_image.gif\n\n "
        "Read the following documentation on how to add images to pack markdown files:\n "
        "https://xsoar.pan.dev/docs/integrations/integration-docs#images"
    )

    result = IntegrationRelativeImagePathValidator().obtain_invalid_content_items(
        content_items
    )
    assert result[0].message == expected


@pytest.mark.parametrize(
    "readme_content,should_fail",
    [
        (
            """# Some Header\n\n## Using commands\nHere are the commands used...\n""",
            False,
        ),
        ("""# Some Header\n\nNo such section here\n""", True),
        ("""# Another\n\n## Using commands\nExtra\n""", False),
        ("""# Another\n\n## Not using commands\nExtra\n""", True),
    ],
)
def test_IsUsingBrandsSectionExistsValidator_obtain_invalid_content_items(
    readme_content, should_fail
):
    """
    Given:
        - A script object with a README file.
        - README may or may not contain the section '## Using commands'.
    When:
        - Running IsUsingBrandsSectionExistsValidator.obtain_invalid_content_items on the script.
    Then:
        - If the README contains '## Using commands', the validator should not fail.
        - If the README does not contain '## Using commands', the validator should return a ValidationResult with the expected error message.
    """
    script = create_script_object(readme_content=readme_content)
    results = IsUsingBrandsSectionExistsValidator().obtain_invalid_content_items(
        [script]
    )
    if should_fail:
        assert len(results) == 1
        assert IsUsingBrandsSectionExistsValidator.error_message in results[0].message
    else:
        assert not results

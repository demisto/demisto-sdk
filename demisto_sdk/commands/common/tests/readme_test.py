import glob
import logging
import os
import sys

import pytest
import requests_mock

import demisto_sdk
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

VALID_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-valid.md"
INVALID_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-invalid.md"
INVALID2_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-invalid2.md"
INVALID3_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-short-invalid.md"
IMAGES_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-images.md"
EMPTY_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-empty.md"
FAKE_INTEGRATION_README = (
    f"{git_path()}/demisto_sdk/tests/test_files/fake_integration/fake_README.md"
)

README_INPUTS = [
    (VALID_MD, True),
    (INVALID_MD, False),
    (INVALID2_MD, False),
    (INVALID3_MD, False),
    (EMPTY_MD, True),
]

MDX_SKIP_NPM_MESSAGE = (
    'Required npm modules are not installed. To run this test you must run "npm install" '
    "in the root of the project."
)


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid(mocker, current, answer):
    from pathlib import Path

    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.get_pack_name",
        return_value="PackName",
    )
    integration_yml = f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml"
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.get_yml_paths_in_dir",
        return_value=([integration_yml], integration_yml),
    )

    mocker.patch.object(Path, "is_file", return_value=answer)
    mocker.patch.object(os.path, "isfile", return_value=answer)
    readme_validator = ReadMeValidator(current)
    integration_yml = f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml"
    valid = ReadMeValidator.are_modules_installed_for_verify(
        readme_validator.content_path
    )
    if not valid:
        pytest.skip("skipping mdx test. " + MDX_SKIP_NPM_MESSAGE)
        return
    with requests_mock.Mocker() as m:
        # Mock get requests
        m.get(
            "https://github.com/demisto/content/blob/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
            status_code=200,
            text="Test1",
        )
        m.get(
            "https://github.com/demisto/content/blob/123/Packs/FeedOffice365/doc_files/test.png",
            status_code=200,
            text="Test2",
        )
        m.get(
            "https://github.com/demisto/content/raw/123/Packs/valid/doc_files/test.png",
            status_code=200,
            text="Test3",
        )
        m.post("http://localhost:6161/", real_http=True)
        with ReadMeValidator.start_mdx_server():
            assert readme_validator.is_valid_file() is answer
        assert not demisto_sdk.commands.common.MDXServer._MDX_SERVER_PROCESS


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid_mdx_server(mocker, current, answer):
    from pathlib import Path

    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.get_pack_name",
        return_value="PackName",
    )
    integration_yml = f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml"
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.get_yml_paths_in_dir",
        return_value=([integration_yml], integration_yml),
    )
    mocker.patch("demisto_sdk.commands.common.tools.sleep")
    mocker.patch.object(Path, "is_file", return_value=answer)
    mocker.patch.object(os.path, "isfile", return_value=answer)

    ReadMeValidator.add_node_env_vars()
    with ReadMeValidator.start_mdx_server():
        readme_validator = ReadMeValidator(current)
        valid = readme_validator.are_modules_installed_for_verify(
            readme_validator.content_path
        )
        if not valid:
            pytest.skip("skipping mdx server test. " + MDX_SKIP_NPM_MESSAGE)
            return
        mocker.patch.dict(os.environ, {"DEMISTO_README_VALIDATION": "yes"})
        assert readme_validator.is_valid_file() is answer


def test_are_modules_installed_for_verify_false_res(tmp_path):
    r = str(tmp_path / "README.md")
    with open(r, "w") as f:
        f.write("Test readme")
    # modules will be missing in tmp_path
    assert not ReadMeValidator.are_modules_installed_for_verify(tmp_path)


def test_air_gapped_env(tmp_path, mocker):
    """
    Given: an environment without docker or node
    When: verifying mdx
    Then: The verification is skipped. If it was not skipped it would error out since the server wasnt started.
    """
    r = str(tmp_path / "README.md")
    with open(r, "w") as f:
        f.write("<div> not valid")
    mocker.patch.object(
        ReadMeValidator, "should_run_mdx_validation", return_value=False
    )
    assert ReadMeValidator(r).is_mdx_file()


def test_relative_url_not_valid(mocker):
    """
    Given
        - A README file with invalid relative urls in it.
    When
        - Run validate on README file
    Then
        - Ensure:
            - Validation fails
            - Both urls were caught correctly
            - Valid url was not caught
            - Image url was not caught
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    absolute_urls = [
        "https://www.good.co.il",
        "https://example.com",
        "https://github.com/demisto/content/blob/123",
        "github.com/demisto/content/blob/123/Packs/FeedOffice365/doc_files/test.png",
        "https://hreftesting.com",
    ]
    relative_urls = [
        "relative1.com",
        "www.relative2.com",
        "hreftesting.com",
        "www.hreftesting.com",
    ]
    readme_validator = ReadMeValidator(INVALID_MD)
    result = readme_validator.verify_readme_relative_urls()
    assert not result
    for url in absolute_urls:
        assert not str_in_call_args_list(logger_error.call_args_list, url)

    for url in relative_urls:
        assert str_in_call_args_list(logger_error.call_args_list, url)

    # no empty links found
    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "[RM112] - Relative urls are not supported within README. If this is not a relative url, please add an "
        "https:// prefix:\n. ",
    )


def test_is_image_path_valid(mocker):
    """
    Given
        - A README file with 2 invalid images paths in it.
    When
        - Run validate on README file
    Then
        - Ensure:
            - Validation fails
            - Both images paths were caught correctly
            - Valid image path was not caught
            - An alternative paths were suggested
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    blob_images_paths = [
        "https://github.com/demisto/content/blob/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
        "https://github.com/demisto/content/blob/123/Packs/FeedOffice365/doc_files/test.png",
    ]
    raw_image_path = (
        "https://github.com/demisto/content/raw/123/Packs/valid/doc_files/test.png"
    )
    raw_images_paths = [
        "https://github.com/demisto/content/raw/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
        "https://github.com/demisto/content/raw/123/Packs/FeedOffice365/doc_files/test.png",
    ]
    assets_images_paths = [
        "https://github.com/demisto/content/assets/91506078/7915b150-bd26-4aed-b4ba-8820226dfe32",
    ]
    readme_validator = ReadMeValidator(INVALID_MD)
    result = readme_validator.is_image_path_valid()

    assert not result
    assert all(
        [
            str_in_call_args_list(logger_error.call_args_list, current_str)
            for current_str in blob_images_paths
        ]
        + [
            str_in_call_args_list(logger_error.call_args_list, current_str)
            for current_str in raw_images_paths
        ]
        + [
            not str_in_call_args_list(logger_error.call_args_list, current_str)
            for current_str in assets_images_paths
        ]
    )
    assert not str_in_call_args_list(logger_error.call_args_list, raw_image_path)


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
def test_unvalid_verify_no_empty_sections(
    integration, file_input, missing_section, mocker
):
    """
    Given
        - Empty sections in different forms
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

    integration.readme.write(file_input)
    readme_path = integration.readme.path

    with ChangeCWD(integration.repo_path):
        readme_validator = ReadMeValidator(readme_path)
        result = readme_validator.verify_no_empty_sections()

        section_error = (
            f"{missing_section} is empty, please elaborate or delete the section."
        )

        assert not result
        assert str_in_call_args_list(logger_error.call_args_list, section_error)


@pytest.mark.parametrize(
    "file_input",
    [
        "## Troubleshooting\n## OtherSection\n## Additional Information\n\n## OtherSection\n##"
    ],
)
def test_combined_unvalid_verify_no_empty_sections(integration, mocker, file_input):
    """
    Given
        - Couple of empty sections
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

    integration.readme.write(file_input)
    readme_path = integration.readme.path

    with ChangeCWD(integration.repo_path):
        readme_validator = ReadMeValidator(readme_path)
        result = readme_validator.verify_no_empty_sections()

        error = (
            "Failed verifying README.md Error Message is: Troubleshooting is empty, please elaborate or delete the"
            " section.\nAdditional Information is empty, please elaborate or delete the section."
        )

        assert not result
        assert str_in_call_args_list(logger_error.call_args_list, error)


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
def test_valid_sections(integration, file_input):
    """
    Given
        - Valid sections in different forms from SECTIONS
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """

    integration.readme.write(file_input)
    readme_path = integration.readme.path
    readme_validator = ReadMeValidator(readme_path)
    result = readme_validator.verify_no_empty_sections()

    assert result


@pytest.mark.parametrize(
    "file_input",
    [
        "## Copyright\ninput",
        "## BSD\n\n---\ninput",
        "## MIT\n\n----------\ninput",
        "## proprietary\n\ninput",
    ],
)
def test_copyright_sections(integration, file_input):
    """
    Given
        - Valid sections in different forms from SECTIONS
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """

    integration.readme.write(file_input)
    readme_path = integration.readme.path
    readme_validator = ReadMeValidator(readme_path)
    result = readme_validator.verify_copyright_section_in_readme_content()

    assert not result


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
def test_verify_no_default_sections_left(integration, mocker, file_input, section):
    """
    Given
        - Readme that contains sections that are created as default and need to be changed
    When
        - Run validate on README file
    Then
        - Ensure no default sections in the readme file
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    integration.readme.write(file_input)
    readme_path = integration.readme.path

    with ChangeCWD(integration.repo_path):
        readme_validator = ReadMeValidator(readme_path)
        result = readme_validator.verify_no_default_sections_left()

        section_error = f'Replace "{section}" with a suitable info.'
        assert not result
        assert str_in_call_args_list(logger_error.call_args_list, section_error)


ERROR_FOUND_CASES = [
    ([f"{FAKE_INTEGRATION_README} - [RM102]"], [], False),
    ([], [f"{FAKE_INTEGRATION_README} - [RM102]"], False),
    ([], [], True),
]


@pytest.mark.parametrize(
    "readme_fake_path, readme_text",
    [
        (
            "/HelloWorld/README.md",
            "getting started and learn how to build an integration",
        )
    ],
)
def test_readme_ignore(integration, readme_fake_path, readme_text):
    """
    Check that packs in ignore list are ignored.
       Given
            - README path of ignore pack
        When
            - Run validate on README of ignored pack
        Then
            - Ensure validation ignored the pack
    """
    integration.readme.write(readme_text)
    readme_path = integration.readme.path
    readme_validator = ReadMeValidator(readme_path)
    # change the pack path to readme_fake_path
    from pathlib import Path

    readme_validator.file_path = Path(readme_fake_path)
    readme_validator.pack_path = readme_validator.file_path.parent

    result = readme_validator.verify_no_default_sections_left()
    assert result


@pytest.mark.parametrize("errors_found, errors_ignore, expected", ERROR_FOUND_CASES)
def test_context_only_runs_once_when_error_exist(
    mocker, integration, errors_found, errors_ignore, expected
):
    """
    Given
        - README that contains changes and YML file
    When
        - Run validate on README file and YML
    Then
        - Ensure validation only run once, either for YML or for README
    """
    readme_validator = ReadMeValidator(FAKE_INTEGRATION_README)
    mocker.patch.object(
        ReadMeValidator, "_get_error_lists", return_value=(errors_found, errors_ignore)
    )

    result = readme_validator.is_context_different_in_yml()
    assert result == expected


DIFFERENCE_CONTEXT_RESULTS_CASE = [
    (
        {
            "zoom-create-user": {
                "only in yml": {"Zoom.User.id"},
                "only in readme": set(),
            }
        },
        False,
    ),
    # case path exists only in yml
    (
        {
            "zoom-list-users": {
                "only in yml": set(),
                "only in readme": {"Zoom.User.last_name", "Zoom.User.first_name"},
            }
        },
        False,
    ),  # case path exists only in readme
    ({}, True),  # case no changes were found
]


@pytest.mark.parametrize("difference_found, expected", DIFFERENCE_CONTEXT_RESULTS_CASE)
def test_context_difference_created_is_valid(mocker, difference_found, expected):
    """
    Given
        - README that contains changes and YML file
    When
        - Run validate on README file and YML
    Then
        - Ensure the difference context is correct
    """
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.compare_context_path_in_yml_and_readme",
        return_value=difference_found,
    )
    readme_validator = ReadMeValidator(FAKE_INTEGRATION_README)
    handle_error_mock = mocker.patch.object(ReadMeValidator, "handle_error")
    valid = readme_validator.is_context_different_in_yml()
    assert valid == expected
    if not valid:
        handle_error_mock.assert_called()
    else:
        handle_error_mock.assert_not_called()


def test_invalid_short_file(mocker):
    """
    Given
        - Non empty Readme with less than 30 chars.
    When
        - Running validate on README file
    Then
        - Ensure verify on Readme fails
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    readme_validator = ReadMeValidator(INVALID3_MD)
    result = readme_validator.verify_readme_is_not_too_short()
    short_readme_error = (
        "Your Pack README is too small (29 chars). Please move its content to the pack "
        "description or add more useful information to the Pack README. "
        "Pack README files are expected to include a few sentences about the pack and/or images."
    )
    assert not result
    assert str_in_call_args_list(logger_error.call_args_list, short_readme_error)


def test_demisto_in_integration_readme(repo):
    """
    Given
        - An integration README contains the word 'Demisto'.

    When
        - Running verify_demisto_in_readme_content.

    Then
        - Ensure that the validation fails.
    """

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("IntName")

    readme_path = glob.glob(
        os.path.join(os.path.dirname(integration.yml.path), "*README.md")
    )[0]

    with open(readme_path, "w") as f:
        f.write("This checks if we have the word Demisto in the README.")

    with ChangeCWD(repo.path):
        readme_validator = ReadMeValidator(integration.readme.path)

        assert not readme_validator.verify_demisto_in_readme_content()


def init_readmeValidator(readme_validator, repo, readme_path):
    readme_validator.content_path = str(repo.path)
    readme_validator.file_path = readme_path
    readme_validator.specific_validations = None


def test_demisto_in_repo_readme(mocker, repo):
    """
    Given
        - A repo README contains the word 'Demisto'.

    When
        - Running verify_demisto_in_readme_content.

    Then
        - Ensure that the validation not fails.
    """
    from pathlib import Path

    readme_path = Path(repo.path) / "README.md"
    mocker.patch.object(ReadMeValidator, "__init__", return_value=None)

    with open(readme_path, "w") as f:
        f.write("This checks if we have the word Demisto in the README.")

    with ChangeCWD(repo.path):
        readme_validator = ReadMeValidator()
        init_readmeValidator(readme_validator, repo, readme_path)
        assert readme_validator.verify_demisto_in_readme_content()


def test_demisto_not_in_readme(repo):
    """
    Given
        - An integration README without the word 'Demisto'.

    When
        - Running verify_demisto_in_readme_content.

    Then
        - Ensure that the validation passes.
    """

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("IntName")

    readme_path = glob.glob(
        os.path.join(os.path.dirname(integration.yml.path), "*README.md")
    )[0]

    with open(readme_path, "w") as f:
        f.write("This checks if we have the word XSOAR in the README.")

    readme_validator = ReadMeValidator(integration.readme.path)

    assert readme_validator.verify_demisto_in_readme_content()


def test_verify_template_not_in_readme(repo):
    """
    Given
        - An integration README contains the generic sentence '%%FILL HERE%%'.

    When
        - Running verify_template_not_in_readme.

    Then
        - Ensure that the validation fails.
    """

    pack = repo.create_pack("PackName")
    integration = pack.create_integration("IntName")

    readme_path = glob.glob(
        os.path.join(os.path.dirname(integration.yml.path), "*README.md")
    )[0]

    with open(readme_path, "w") as f:
        f.write("This checks if we have the sentence %%FILL HERE%% in the README.")

    with ChangeCWD(repo.path):
        readme_validator = ReadMeValidator(integration.readme.path)

        assert not readme_validator.verify_template_not_in_readme()


def test_verify_readme_image_paths(mocker):
    """

    Given
           - A README file (not pack README) with valid/invalid relative image
            paths and valid/invalid absolute image paths in it.
       When
           - Run validate on README file
       Then
           - Ensure:
               - Validation fails
               - Image paths were caught correctly
               - Valid paths are not caught
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    readme_validator = ReadMeValidator(IMAGES_MD)
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch("demisto_sdk.commands.common.tools.sleep")

    with requests_mock.Mocker() as m:
        # Mock get requests
        m.get(
            "https://github.com/demisto/test1.png",
            status_code=404,
            text="Test1",
            reason="just because",
        )
        m.get(
            "https://github.com/demisto/content/raw/test2.png",
            status_code=404,
            text="Test2",
        )
        m.get("https://github.com/demisto/test3.png", status_code=200, text="Test3")
        m.get(
            "https://raw.githubusercontent.com/demisto/content/master/Packs/132/some_image.png",
            status_code=200,
            text="Test4",
        )
        is_valid = readme_validator.verify_readme_image_paths()

    sys.stdout = sys.__stdout__  # reset stdout.
    assert not is_valid
    assert all(
        [
            str_in_call_args_list(
                logger_error.call_args_list,
                "The following image relative path is not valid, please recheck it:\n",
            ),
            str_in_call_args_list(
                logger_error.call_args_list,
                "../../default.png",
            ),
            str_in_call_args_list(
                logger_error.call_args_list,
                "Branch name was found in the URL, please change it to the commit hash:\n",
            ),
            str_in_call_args_list(
                logger_error.call_args_list,
                "\n".join(
                    (
                        "[RM108] - Error in readme image: got HTTP response code 404, reason = just because",
                        "The following image link seems to be broken, please repair it:",
                        "https://github.com/demisto/test1.png",
                    )
                ),
            ),
            str_in_call_args_list(
                logger_error.call_args_list,
                "\n".join(
                    (
                        "[RM108] - Error in readme image: got HTTP response code 404 ",
                        "The following image link seems to be broken, please repair it:",
                        "https://github.com/demisto/content/raw/test2.png",
                    )
                ),
            ),
        ]
    )

    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "The following image relative path is not valid, please recheck it:\n"
        "default.png",
    )
    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "Branch name was found in the URL, please change it to the commit hash:\n"
        "https://raw.githubusercontent.com/demisto/content/123456/Packs/CommonPlaybooks/doc_files/some_image.png",
    )
    assert not str_in_call_args_list(
        logger_error.call_args_list,
        "please repair it:\n" "https://github.com/demisto/test3.png",
    )


def test_check_readme_relative_image_paths(mocker):
    """

    Given
        - A README file (not pack README) with invalid relative image
         paths and invalid absolute image paths in it.
    When
        - Run validate on README file and ignoring RM108 error
    Then
        - Ensure:
            - Validation pass.
            - nothing is printed as error.

    """
    readme_validator = ReadMeValidator(IMAGES_MD, ignored_errors={IMAGES_MD: "RM108"})
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    with requests_mock.Mocker() as m:
        # Mock get requests
        m.get(
            "https://github.com/demisto/test1.png",
            status_code=404,
            text="Test1",
            reason="just because",
        )
        m.get(
            "https://github.com/demisto/content/raw/test2.png",
            status_code=404,
            text="Test2",
        )
        m.get("https://github.com/demisto/test3.png", status_code=200, text="Test3")
        formatted_errors = readme_validator.check_readme_relative_image_paths()

    assert not formatted_errors


@pytest.mark.parametrize("current, answer", README_INPUTS[:2])
def test_verify_image_exist(mocker, current, answer):
    from pathlib import Path

    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.get_pack_name",
        return_value="PackName",
    )
    mocker.patch.object(Path, "is_file", return_value=answer)

    assert ReadMeValidator(current).verify_image_exist() == answer

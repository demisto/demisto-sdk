import glob
import os

import pytest
import requests_mock

import demisto_sdk
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from TestSuite.test_tools import ChangeCWD

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


def test_is_image_path_valid(mocker, caplog):
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
        [current_str in caplog.text for current_str in blob_images_paths]
        + [current_str in caplog.text for current_str in raw_images_paths]
        + [current_str not in caplog.text for current_str in assets_images_paths]
    )
    assert raw_image_path not in caplog.text


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
    integration, file_input, missing_section, mocker, caplog
):
    """
    Given
        - Empty sections in different forms
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    integration.readme.write(file_input)
    readme_path = integration.readme.path

    with ChangeCWD(integration.repo_path):
        readme_validator = ReadMeValidator(readme_path)
        result = readme_validator.verify_no_empty_sections()

        section_error = (
            f"{missing_section} is empty, please elaborate or delete the section."
        )

        assert not result
        assert section_error in caplog.text


@pytest.mark.parametrize(
    "file_input",
    [
        "## Troubleshooting\n## OtherSection\n## Additional Information\n\n## OtherSection\n##"
    ],
)
def test_combined_unvalid_verify_no_empty_sections(
    integration, mocker, file_input, caplog
):
    """
    Given
        - Couple of empty sections
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """

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
        assert error in caplog.text


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
def test_verify_no_default_sections_left(
    integration, mocker, file_input, section, caplog
):
    """
    Given
        - Readme that contains sections that are created as default and need to be changed
    When
        - Run validate on README file
    Then
        - Ensure no default sections in the readme file
    """
    integration.readme.write(file_input)
    readme_path = integration.readme.path

    with ChangeCWD(integration.repo_path):
        readme_validator = ReadMeValidator(readme_path)
        result = readme_validator.verify_no_default_sections_left()

        assert f'Replace "{section}" with a suitable info.' in caplog.text
        assert not result


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


@pytest.mark.parametrize(
    "error_code_to_ignore, expected_result",
    [({"README.md": "RM100"}, True), ({}, False)],
)
def test_readme_verify_no_default_ignore_test(
    error_code_to_ignore, expected_result, integration
):
    """
    Given:
        - A readme that violates a validation and the ignore error code for the validation.
        - A readme that violates a validation without the ignore error code for the validation.

    When:
        - When running the validate command on a readme file.

    Then:
        - Validate that when the error code is ignored, the validation passes.
        - Validate that when the error code is not ignored, the validation fails.
    """
    readme_text = "This is a test readme running on version xx"
    readme_path = "fake_path"
    integration.readme.write(readme_text)
    readme_path = integration.readme.path
    readme_validator = ReadMeValidator(readme_path, ignored_errors=error_code_to_ignore)
    assert readme_validator.verify_no_default_sections_left() == expected_result


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


def test_invalid_short_file(mocker, caplog):
    """
    Given
        - Non empty Readme with less than 30 chars.
    When
        - Running validate on README file
    Then
        - Ensure verify on Readme fails
    """
    readme_validator = ReadMeValidator(INVALID3_MD)
    result = readme_validator.verify_readme_is_not_too_short()
    short_readme_error = (
        "Your Pack README is too small (29 chars). Please move its content to the pack "
        "description or add more useful information to the Pack README. "
        "Pack README files are expected to include a few sentences about the pack and/or images."
    )
    assert not result
    assert short_readme_error in caplog.text


def init_readmeValidator(readme_validator, repo, readme_path):
    readme_validator.content_path = str(repo.path)
    readme_validator.file_path = readme_path
    readme_validator.specific_validations = None


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


@pytest.mark.parametrize("current, answer", README_INPUTS[:2])
def test_verify_image_exist(mocker, current, answer):
    from pathlib import Path

    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.readme.get_pack_name",
        return_value="PackName",
    )
    mocker.patch.object(Path, "is_file", return_value=answer)

    assert ReadMeValidator(current).verify_image_exist() == answer

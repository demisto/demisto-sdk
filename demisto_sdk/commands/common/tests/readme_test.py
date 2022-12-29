import glob
import io
import os
import sys

import pytest
import requests
import requests_mock
from requests.adapters import HTTPAdapter
from urllib3 import Retry

import demisto_sdk
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.MDXServer import start_local_MDX_server
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
    readme_validator = ReadMeValidator(current)
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
        mocker.patch.dict(
            os.environ,
            {"DEMISTO_README_VALIDATION": "yes", "DEMISTO_MDX_CMD_VERIFY": "yes"},
        )
        assert readme_validator.is_valid_file() is answer
        assert not demisto_sdk.commands.common.MDXServer._MDX_SERVER_PROCESS


def test_local_server_up_and_down():
    """
    Given:
        - node dependencies installed
        - a valid file for mdx
    When:
        starting a local server with an mdx server
    Then:
        - The server is started successfully.
        - The call is successful.
    """
    ReadMeValidator.add_node_env_vars()
    readme_validator = ReadMeValidator(VALID_MD)
    valid = ReadMeValidator.are_modules_installed_for_verify(
        readme_validator.content_path
    )
    if not valid:
        pytest.skip("skipping mdx server test. " + MDX_SKIP_NPM_MESSAGE)
        return

    with start_local_MDX_server() as started:
        assert started
        assert_successful_mdx_call()


def assert_successful_mdx_call():
    session = requests.Session()
    retry = Retry(total=2)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    response = session.request(
        "POST", "http://localhost:6161", data="## Hello", timeout=20
    )
    assert response.status_code == 200


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid_mdx_server(mocker, current, answer):
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


def test_local_server_is_up():
    """
    Given:
        A valid file for mdx
    When:
        starting a local server and checking if up inside the context
    Then:
        - The if statement passes
        - The api call succeeds
    """
    readme_validator = ReadMeValidator(INVALID_MD)
    valid = ReadMeValidator.are_modules_installed_for_verify(
        readme_validator.content_path
    )
    if not valid:
        pytest.skip("skipping mdx server test. " + MDX_SKIP_NPM_MESSAGE)
        return
    with start_local_MDX_server():
        if start_local_MDX_server():
            assert_successful_mdx_call()
        assert_successful_mdx_call()


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


def test_relative_url_not_valid():
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
    captured_output = io.StringIO()
    sys.stdout = captured_output  # redirect stdout.
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
    sys.stdout = sys.__stdout__  # reset stdout.
    assert not result
    output = captured_output.getvalue()
    for url in absolute_urls:
        assert url not in output

    for url in relative_urls:
        assert url in output

    # no empty links found
    assert (
        "[RM112] - Relative urls are not supported within README. If this is not a relative url, please add an "
        "https:// prefix:\n. " not in output
    )


def test_is_image_path_valid():
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
    captured_output = io.StringIO()
    sys.stdout = captured_output  # redirect stdout.
    images_paths = [
        "https://github.com/demisto/content/blob/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
        "https://github.com/demisto/content/blob/123/Packs/FeedOffice365/doc_files/test.png",
        "https://github.com/demisto/content/raw/123/Packs/valid/doc_files/test.png",
    ]
    alternative_images_paths = [
        "https://github.com/demisto/content/raw/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
        "https://github.com/demisto/content/raw/123/Packs/FeedOffice365/doc_files/test.png",
    ]
    readme_validator = ReadMeValidator(INVALID_MD)
    result = readme_validator.is_image_path_valid()
    sys.stdout = sys.__stdout__  # reset stdout.
    assert not result
    assert images_paths[0] and alternative_images_paths[0] in captured_output.getvalue()
    assert images_paths[1] and alternative_images_paths[1] in captured_output.getvalue()
    assert images_paths[2] not in captured_output.getvalue()


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
    integration, capsys, file_input, missing_section
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

        stdout, _ = capsys.readouterr()
        section_error = (
            f"{missing_section} is empty, please elaborate or delete the section."
        )

        assert not result
        assert section_error in stdout


@pytest.mark.parametrize(
    "file_input",
    [
        "## Troubleshooting\n## OtherSection\n## Additional Information\n\n## OtherSection\n##"
    ],
)
def test_combined_unvalid_verify_no_empty_sections(integration, capsys, file_input):
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

        stdout, _ = capsys.readouterr()
        error = (
            "Failed verifying README.md Error Message is: Troubleshooting is empty, please elaborate or delete the"
            " section.\nAdditional Information is empty, please elaborate or delete the section."
        )

        assert not result
        assert error in stdout


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
            "This integration was integrated and tested with version xx of integration v2",
            "version xx",
        ),
        (
            "##Dummy Integration\n this integration is for getting started and learn how to build an "
            "integration. some extra text here",
            "getting started and learn how to build an integration",
        ),
    ],
)
def test_verify_no_default_sections_left(integration, capsys, file_input, section):
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

        stdout, _ = capsys.readouterr()
        section_error = f'Replace "{section}" with a suitable info.'
        assert not result
        assert section_error in stdout


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


def test_invalid_short_file(capsys):
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
    stdout, _ = capsys.readouterr()
    short_readme_error = (
        "Your Pack README is too small (29 chars). Please move its content to the pack "
        "description or add more useful information to the Pack README. "
        "Pack README files are expected to include a few sentences about the pack and/or images."
    )
    assert not result
    assert short_readme_error in stdout


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
    captured_output = io.StringIO()
    sys.stdout = captured_output  # redirect stdout.

    readme_validator = ReadMeValidator(IMAGES_MD)
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
        is_valid = readme_validator.verify_readme_image_paths()

    sys.stdout = sys.__stdout__  # reset stdout.
    captured_output = captured_output.getvalue()
    assert not is_valid
    assert (
        "The following image relative path is not valid, please recheck it:\n"
        "![Identity with High Risk Score](../../default.png)" in captured_output
    )
    assert (
        "The following image relative path is not valid, please recheck it:\n"
        "![Identity with High Risk Score](default.png)" not in captured_output
    )
    assert (
        "Branch name was found in the URL, please change it to the commit hash:\n"
        "![branch in url]" in captured_output
    )
    assert (
        "Branch name was found in the URL, please change it to the commit hash:\n"
        "![commit hash in url]" not in captured_output
    )
    assert (
        "\n".join(
            (
                "[RM108] - Error in readme image: got HTTP response code 404, reason = just because",
                "The following image link seems to be broken, please repair it:",
                "![Identity with High Risk Score](https://github.com/demisto/test1.png)",
            )
        )
        in captured_output
    )
    assert (
        "\n".join(
            (
                "[RM108] - Error in readme image: got HTTP response code 404 ",
                "The following image link seems to be broken, please repair it:",
                "(https://github.com/demisto/content/raw/test2.png)",
            )
        )
        in captured_output
    )
    assert (
        "please repair it:\n"
        "![Identity with High Risk Score](https://github.com/demisto/test3.png)"
        not in captured_output
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

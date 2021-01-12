import io
import os
import sys

import pytest
from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Readme
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK_README = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'README.md'


def mock_readme(repo):
    pack = repo.create_pack('Temp')
    integration = pack.create_integration()
    integration.create_default_integration()
    return integration.readme


def test_objects_factory_pack_readme():
    obj = path_to_pack_object(PACK_README)
    assert isinstance(obj, Readme)


def test_objects_factory_integration_readme(repo):
    readme = mock_readme(repo)
    obj = path_to_pack_object(readme.path)
    assert isinstance(obj, Readme)


def test_prefix_pack_readme():
    obj = Readme(PACK_README)
    assert obj.normalize_file_name() == PACK_README.name


def test_prefix_readme(repo):
    readme = mock_readme(repo)
    obj = Readme(readme.path)
    assert obj.normalize_file_name() == 'README.md'


VALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-valid.md'
INVALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid.md'
INVALID2_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid2.md'

README_INPUTS = [
    (VALID_MD, True),
    (INVALID_MD, False),
    (INVALID2_MD, False),
]

MDX_SKIP_NPM_MESSAGE = 'Required npm modules are not installed. To run this test you must run "npm install" ' \
                       'in the root of the project.'


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid(mocker, current, answer, repo):
    readme_obj = Readme(current)
    valid = readme_obj.are_modules_installed_for_verify(readme_obj.content_path)
    if not valid:
        pytest.skip('skipping mdx test. ' + MDX_SKIP_NPM_MESSAGE)
        return
    mocker.patch.dict(os.environ, {'DEMISTO_README_VALIDATION': 'yes', 'DEMISTO_MDX_CMD_VERIFY': 'yes'})
    assert readme_obj.is_valid_file() is answer
    assert not readme_obj._MDX_SERVER_PROCESS


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid_mdx_server(mocker, current, answer):
    readme_obj = Readme(current)
    valid = readme_obj.are_modules_installed_for_verify(readme_obj.content_path)
    if not valid:
        pytest.skip('skipping mdx server test. ' + MDX_SKIP_NPM_MESSAGE)
        return
    mocker.patch.dict(os.environ, {'DEMISTO_README_VALIDATION': 'yes'})
    assert readme_obj.is_valid_file() is answer
    assert readme_obj._MDX_SERVER_PROCESS is not None
    readme_obj.stop_mdx_server()


def test_are_modules_installed_for_verify_false_res(tmp_path, repo):
    readme = mock_readme(repo)
    readme.write('Test readme')
    readme_obj = Readme(readme.path)
    # modules will be missing in tmp_path
    assert not readme_obj.are_modules_installed_for_verify(readme_obj.content_path)


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
    images_paths = ["https://github.com/demisto/content/blob/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
                    "https://github.com/demisto/content/blob/123/Packs/FeedOffice365/doc_files/test.png",
                    "https://github.com/demisto/content/raw/123/Packs/valid/doc_files/test.png"]
    alternative_images_paths = [
        "https://github.com/demisto/content/raw/123/Packs/AutoFocus/doc_files/AutoFocusPolling.png",
        "https://github.com/demisto/content/raw/123/Packs/FeedOffice365/doc_files/test.png"]
    readme_obj = Readme(INVALID_MD)
    result = readme_obj.is_image_path_valid()
    sys.stdout = sys.__stdout__   # reset stdout.
    assert not result
    assert images_paths[0] and alternative_images_paths[0] in captured_output.getvalue()
    assert images_paths[1] and alternative_images_paths[1] in captured_output.getvalue()
    assert images_paths[2] not in captured_output.getvalue()


@pytest.mark.parametrize("file_input, missing_section",
                         [("## Troubleshooting\n## OtherSection", "Troubleshooting"),
                          ("## Troubleshooting", "Troubleshooting"),
                          ("## Troubleshooting\n\n---\n## OtherSection", "Troubleshooting"),
                          ("## Use Cases\n\n----------\n## OtherSection", "Use Cases"),
                          ("## Additional Information\n\n## OtherSection", "Additional Information"),
                          ("## Known Limitations\n\n----------\n", "Known Limitations")])
def test_unvalid_verify_no_empty_sections(capsys, file_input, missing_section, repo):
    """
    Given
        - Empty sections in different forms
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """

    readme = mock_readme(repo)
    readme.write(file_input)
    readme_obj = Readme(readme.path)
    result = readme_obj.verify_no_empty_sections()

    stdout, _ = capsys.readouterr()
    section_error = f'{missing_section} is empty, please elaborate or delete the section.'

    assert not result
    assert section_error in stdout


@pytest.mark.parametrize("file_input",
                         ["## Troubleshooting\n## OtherSection\n## Additional Information\n\n## OtherSection\n##"])
def test_combined_unvalid_verify_no_empty_sections(repo, capsys, file_input):
    """
    Given
        - Couple of empty sections
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    readme = mock_readme(repo)
    readme.write(file_input)
    readme_obj = Readme(readme.path)
    result = readme_obj.verify_no_empty_sections()

    stdout, _ = capsys.readouterr()
    error = 'Failed verifying README.md Error Message is: Troubleshooting is empty, please elaborate or delete the' \
            ' section.\nAdditional Information is empty, please elaborate or delete the section.'

    assert not result
    assert error in stdout


@pytest.mark.parametrize("file_input",
                         ["## Troubleshooting\ninput",
                          "## Troubleshooting\n\n---\ninput",
                          "## Use Cases\n\n----------\ninput",
                          "## Additional Information\n\ninput",
                          "## Additional Information\n\n### OtherSection",
                          "## Known Limitations\n\n----------\ninput"])
def test_valid_sections(repo, file_input):
    """
    Given
        - Valid sections in different forms from SECTIONS
    When
        - Run validate on README file
    Then
        - Ensure no empty sections from the SECTIONS list
    """
    readme = mock_readme(repo)
    readme.write(file_input)
    readme_obj = Readme(readme.path)
    result = readme_obj.verify_no_empty_sections()
    assert result


@pytest.mark.parametrize("file_input, section",
                         [("##### Required Permissions\n**FILL IN REQUIRED PERMISSIONS HERE**\n##### Base Command",
                           'FILL IN REQUIRED PERMISSIONS HERE'),
                          ("##### Required Permissions **FILL IN REQUIRED PERMISSIONS HERE**\n##### Base Command",
                           'FILL IN REQUIRED PERMISSIONS HERE'),
                          ("##### Required Permissions FILL IN REQUIRED PERMISSIONS HERE",
                           'FILL IN REQUIRED PERMISSIONS HERE'),
                          ("##### Required Permissions FILL IN REQUIRED PERMISSIONS HERE",
                           'FILL IN REQUIRED PERMISSIONS HERE'),
                          ("This integration was integrated and tested with version xx of integration v2",
                           'version xx')])
def test_verify_no_default_sections_left(repo, capsys, file_input, section):
    """
    Given
        - Read me that contains sections that are created as default and need to be changed
    When
        - Run validate on README file
    Then
        - Ensure no default sections in the readme file
    """
    readme = mock_readme(repo)
    readme.write(file_input)
    readme_validator = Readme(readme.path)
    result = readme_validator.verify_no_default_sections_left()

    stdout, _ = capsys.readouterr()
    section_error = f'Replace "{section}" with a suitable info.'
    assert not result
    assert section_error in stdout

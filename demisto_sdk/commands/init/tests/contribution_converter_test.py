import json
import os
import re
import shutil
from typing import Union
from zipfile import ZipFile

import pytest
from _pytest.fixtures import FixtureRequest
from _pytest.tmpdir import TempPathFactory, _mk_tmp
from mock import patch

from demisto_sdk.commands.common.constants import LAYOUT, LAYOUTS_CONTAINER
from demisto_sdk.commands.init.contribution_converter import \
    ContributionConverter
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from TestSuite.contribution import Contribution
from TestSuite.repo import Repo

RELEASE_NOTES_COPY = "demisto_sdk/commands/init/tests/RN/1_0_1-formatted.md"
SOURCE_RELEASE_NOTES_FILE = "demisto_sdk/commands/init/tests/RN/1_0_1.md"
EXPECTED_RELEASE_NOTES = "demisto_sdk/commands/init/tests/RN/1_0_1_expected.md"

name_reformatting_test_examples = [
    ('PACKYAYOK', 'PACKYAYOK'),
    ('PackYayOK', 'PackYayOK'),
    ('pack yay ok!', 'PackYayOk'),
    ('PackYayOK', 'PackYayOK'),
    ('-pack-yay-ok--', 'Pack-Yay-Ok'),
    ('PackYayOK', 'PackYayOK'),
    ('The quick brown fox, jumps over the lazy dog!', 'TheQuickBrownFox_JumpsOverTheLazyDog'),
    ('The quick`*+.brown fox, ;jumps over @@the lazy dog!', 'TheQuick_BrownFox_JumpsOver_TheLazyDog'),
    ('ThE quIck`*+.brown fox, ;jumps ovER @@the lazy dog!', 'ThEQuIck_BrownFox_JumpsOvER_TheLazyDog')
]


def util_open_file(path):
    with open(path, mode='r') as f:
        return f.read()


@pytest.fixture
def contrib_converter():
    return ContributionConverter('')


def create_contribution_converter(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> ContributionConverter:
    tmp_dir = _mk_tmp(request, tmp_path_factory)
    return ContributionConverter(name=request.param, base_dir=str(tmp_dir))


@pytest.fixture
def contribution_converter(request: FixtureRequest, tmp_path_factory: TempPathFactory) -> ContributionConverter:
    """Mocking tmp_path
    """
    return create_contribution_converter(request, tmp_path_factory)


def rename_file_in_zip(path_to_zip: Union[os.PathLike, str], original_file_name: str, updated_file_name: str):
    """Utility to rename a file in a zip file

    Useful for renaming files in an example contribution zip file to test specific cases.
    If the zipped file includes directories, make sure the filenames take that into account.

    Args:
        path_to_zip (Union[os.PathLike, str]): The zip file containing a file which needs renaming
        original_file_name (str): The file which will be renamed
        updated_file_name (str): The name the original file will be renamed to
    """
    modded_zip_file = os.path.join(os.path.dirname(path_to_zip), 'Edit' + os.path.basename(path_to_zip))
    tmp_zf = ZipFile(modded_zip_file, 'w')
    with ZipFile(path_to_zip, 'r') as zf:
        for item in zf.infolist():
            if item.filename == original_file_name:
                with tmp_zf.open(updated_file_name, 'w') as out_file:
                    out_file.write(zf.read(item.filename))
            else:
                tmp_zf.writestr(item, zf.read(item.filename))
    os.replace(modded_zip_file, path_to_zip)


@patch('demisto_sdk.commands.split.ymlsplitter.get_python_version')
@patch('demisto_sdk.commands.init.contribution_converter.get_content_path')
def test_convert_contribution_zip_updated_pack(get_content_path_mock, get_python_version_mock, tmp_path):
    """
    Create a fake contribution zip file and test that it is converted to a Pack correctly.
    The pack already exists, checking the update flow.

    Args:
        get_content_path_mock (MagicMock): Patch of the 'get_content_path' function to return the fake repo directory
            used in the test
        get_python_version_mock (MagicMock): Patch of the 'get_python_version' function to return the "3.7"
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file.

    Given
    - A contribution zip file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    - The contribution is an update to an existing pack
    Then
    - Ensure integration are componentized and in valid directory structure
    - Ensure that readme file has not been changed.

    """
    # Create all Necessary Temporary directories
    # create temp directory for the repo
    repo_dir = tmp_path / 'content_repo'
    repo_dir.mkdir()
    get_content_path_mock.return_value = repo_dir
    get_python_version_mock.return_value = 3.7
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = repo_dir / 'target_dir'
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / 'contrib_zip'
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    repo = Repo(repo_dir)
    pack = repo.create_pack('TestPack')
    integration = pack.create_integration('integration0')
    integration.create_default_integration()
    contrib_zip = Contribution(target_dir, 'ContribTestPack', repo)
    contrib_zip.create_zip(contribution_zip_dir)
    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()
    name = 'Test Pack'
    contribution_path = contrib_zip.created_zip_filepath
    description = 'test pack description here'
    author = 'Octocat Smith'
    contrib_converter_inst = ContributionConverter(
        name=name, contribution=contribution_path, description=description, author=author, create_new=False,
        no_pipenv=True)
    contrib_converter_inst.convert_contribution_to_pack()
    converted_pack_path = repo_dir / 'Packs' / 'TestPack'
    assert converted_pack_path.exists()
    integrations_path = converted_pack_path / 'Integrations'
    sample_integration_path = integrations_path / 'integration0'
    integration_yml = sample_integration_path / 'integration0.yml'
    integration_py = sample_integration_path / 'integration0.py'
    integration_description = sample_integration_path / 'integration0_description.md'
    integration_image = sample_integration_path / 'integration0_image.png'
    integration_readme_md = sample_integration_path / 'README.md'
    unified_yml = integrations_path / 'integration-integration0.yml'
    unified_yml_in_sample = sample_integration_path / 'integration-integration0.yml'
    integration_files = [integration_yml, integration_py, integration_description, integration_image,
                         integration_readme_md]
    for integration_file in integration_files:
        assert integration_file.exists()
    # In a new pack that part will exist.

    assert not unified_yml.exists()
    assert not unified_yml_in_sample.exists()


@patch('demisto_sdk.commands.split.ymlsplitter.get_python_version')
@patch('demisto_sdk.commands.init.contribution_converter.get_content_path')
def test_convert_contribution_zip_outputs_structure(get_content_path_mock, get_python_version_mock, tmp_path):
    """Create a fake contribution zip file and test that it is converted to a Pack correctly

    Args:
        get_content_path_mock (MagicMock): Patch of the 'get_content_path' function to return the fake repo directory
            used in the test
        get_python_version_mock (MagicMock): Patch of the 'get_python_version' function to return the "3.7"
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file

    Given
    - A contribution zip file
    - The zipfile contains a unified script file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure the unified yaml files of the integration and script have been removed from the output created by
      converting the contribution zip file
    """
    # ### SETUP ### #
    # Create all Necessary Temporary directories
    # create temp directory for the repo
    repo_dir = tmp_path / 'content_repo'
    repo_dir.mkdir()
    get_content_path_mock.return_value = repo_dir
    get_python_version_mock.return_value = 3.7
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = repo_dir / 'target_dir'
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / 'contrib_zip'
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    repo = Repo(repo_dir)
    contrib_zip = Contribution(target_dir, 'ContribTestPack', repo)
    contrib_zip.create_zip(contribution_zip_dir)
    # Convert Zip
    name = 'Contrib Test Pack'
    contribution_path = contrib_zip.created_zip_filepath
    description = 'test pack description here'
    author = 'Octocat Smith'
    contrib_converter_inst = ContributionConverter(
        name=name, contribution=contribution_path, description=description, author=author, no_pipenv=True)
    contrib_converter_inst.convert_contribution_to_pack()

    # Ensure directory/file structure output by conversion meets expectations

    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()

    converted_pack_path = repo_dir / 'Packs' / 'ContribTestPack'
    assert converted_pack_path.exists()

    scripts_path = converted_pack_path / 'Scripts'
    sample_script_path = scripts_path / 'SampleScript'
    script_yml = sample_script_path / 'SampleScript.yml'
    script_py = sample_script_path / 'SampleScript.py'
    script_readme_md = sample_script_path / 'README.md'
    unified_script_in_sample = sample_script_path / 'automation-script0.yml'
    unified_script = scripts_path / 'automation-script0.yml'

    assert scripts_path.exists()
    assert sample_script_path.exists()
    assert script_yml.exists()
    assert script_py.exists()
    assert script_readme_md.exists()

    # generated script readme should not be empty
    script_statinfo = os.stat(script_readme_md)
    assert script_statinfo and script_statinfo.st_size > 0
    # unified yaml of the script should have been deleted
    assert not unified_script_in_sample.exists()
    assert not unified_script.exists()

    integrations_path = converted_pack_path / 'Integrations'
    sample_integration_path = integrations_path / 'Sample'
    integration_yml = sample_integration_path / 'Sample.yml'
    integration_py = sample_integration_path / 'Sample.py'
    integration_description = sample_integration_path / 'Sample_description.md'
    integration_image = sample_integration_path / 'Sample_image.png'
    integration_readme_md = sample_integration_path / 'README.md'
    unified_yml = integrations_path / 'integration-integration0.yml'
    unified_yml_in_sample = sample_integration_path / 'integration-integration0.yml'
    integration_files = [integration_yml, integration_py, integration_description, integration_image,
                         integration_readme_md]
    for integration_file in integration_files:
        assert integration_file.exists()
    # generated integration readme should not be empty
    statinfo = os.stat(integration_readme_md)
    assert statinfo and statinfo.st_size > 0

    # unified yaml of the integration should have been deleted
    assert not unified_yml.exists()
    assert not unified_yml_in_sample.exists()


@patch('demisto_sdk.commands.split.ymlsplitter.get_python_version')
@patch('demisto_sdk.commands.init.contribution_converter.get_content_path')
def test_convert_contribution_zip(get_content_path_mock, get_python_version_mock, tmp_path):
    """Create a fake contribution zip file and test that it is converted to a Pack correctly

    Args:
        get_content_path_mock (MagicMock): Patch of the 'get_content_path' function to return the fake repo directory
            used in the test
        get_python_version_mock (MagicMock): Patch of the 'get_python_version' function to return the "3.7"
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file

    Given
    - A contribution zip file
    - The zipfile contains a unified script file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure script and integration are componentized and in valid directory structure
    - Ensure readme_files is not empty and the generated docs exists.
    """
    # Create all Necessary Temporary directories
    # create temp directory for the repo
    repo_dir = tmp_path / 'content_repo'
    repo_dir.mkdir()
    get_content_path_mock.return_value = repo_dir
    get_python_version_mock.return_value = 3.7
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = repo_dir / 'target_dir'
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / 'contrib_zip'
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    repo = Repo(repo_dir)
    contrib_zip = Contribution(target_dir, 'ContribTestPack', repo)
    contrib_zip.create_zip(contribution_zip_dir)
    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()

    # rename script-script0.yml unified to automation-script0.yml
    # this naming is aligned to how the server exports scripts in contribution zips
    rename_file_in_zip(
        contrib_zip.created_zip_filepath, 'automation/script-script0.yml', 'automation/automation-script0.yml'
    )

    name = 'Contrib Test Pack'
    contribution_path = contrib_zip.created_zip_filepath
    description = 'test pack description here'
    author = 'Octocat Smith'
    contrib_converter_inst = ContributionConverter(
        name=name, contribution=contribution_path, description=description, author=author, no_pipenv=True)
    contrib_converter_inst.convert_contribution_to_pack()

    converted_pack_path = repo_dir / 'Packs' / 'ContribTestPack'
    assert converted_pack_path.exists()

    scripts_path = converted_pack_path / 'Scripts'
    sample_script_path = scripts_path / 'SampleScript'
    script_yml = sample_script_path / 'SampleScript.yml'
    script_py = sample_script_path / 'SampleScript.py'
    script_readme_md = sample_script_path / 'README.md'
    unified_script_in_sample = sample_script_path / 'automation-script0.yml'
    unified_script = scripts_path / 'automation-script0.yml'

    assert scripts_path.exists()
    assert sample_script_path.exists()
    assert script_yml.exists()
    assert script_py.exists()
    assert script_readme_md.exists()
    assert not unified_script_in_sample.exists()
    assert not unified_script.exists()

    integrations_path = converted_pack_path / 'Integrations'
    sample_integration_path = integrations_path / 'Sample'
    integration_yml = sample_integration_path / 'Sample.yml'
    integration_py = sample_integration_path / 'Sample.py'
    integration_description = sample_integration_path / 'Sample_description.md'
    integration_image = sample_integration_path / 'Sample_image.png'
    integration_readme_md = sample_integration_path / 'README.md'
    unified_yml = integrations_path / 'integration-integration0.yml'
    unified_yml_in_sample = sample_integration_path / 'integration-integration0.yml'
    integration_files = [integration_yml, integration_py, integration_description, integration_image,
                         integration_readme_md]
    for integration_file in integration_files:
        assert integration_file.exists()
    assert not unified_yml.exists()
    assert not unified_yml_in_sample.exists()

    playbooks_path = converted_pack_path / 'Playbooks'
    playbook_yml = playbooks_path / 'playbook-SamplePlaybook.yml'
    playbook_readme_md = playbooks_path / 'README.md'

    assert playbooks_path.exists()
    assert playbook_yml.exists()
    assert playbook_readme_md.exists()

    layouts_path = converted_pack_path / 'Layouts'
    sample_layoutscontainer = layouts_path / f'{LAYOUTS_CONTAINER}-fakelayoutscontainer.json'
    sample_layout = layouts_path / f'{LAYOUT}-fakelayout.json'

    assert layouts_path.exists()
    assert sample_layoutscontainer.exists()
    assert sample_layout.exists()

    assert set(contrib_converter_inst.readme_files) == {str(playbook_readme_md), str(integration_readme_md),
                                                        str(script_readme_md)}


@patch('demisto_sdk.commands.split.ymlsplitter.get_python_version')
@patch('demisto_sdk.commands.init.contribution_converter.get_content_path')
def test_convert_contribution_zip_with_args(get_content_path_mock, get_python_version_mock, tmp_path):
    '''Convert a contribution zip to a pack and test that the converted pack's 'pack_metadata.json' is correct

    Args:
        get_content_path_mock (MagicMock): Patch of the 'get_content_path' function to return the fake repo directory
            used in the test
        get_python_version_mock (MagicMock): Patch of the 'get_python_version' function to return the "3.7"
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate converting a contribution zip file

    Given
    - A contribution zip file
    When
    - The contrib_converter class instance is instantiated with the 'name' argument of 'Test Pack'
    - The contrib_converter class instance is instantiated with the 'description' argument
      of 'test pack description here'
    - The contrib_converter class instance is instantiated with the 'author' argument of 'Octocat Smith'
    - The contrib_converter class instance is instantiated with the 'gh_user' argument of 'octocat'
    Then
    - Ensure pack with directory name of 'TestPack' is created
    - Ensure that the pack's 'pack_metadata.json' file's 'name' field is 'Test Pack'
    - Ensure that the pack's 'pack_metadata.json' file's 'description' field is 'test pack description here'
    - Ensure that the pack's 'pack_metadata.json' file's 'author' field is 'Octocat Smith'
    - Ensure that the pack's 'pack_metadata.json' file's 'githubUser' field a list containing only 'octocat'
    - Ensure that the pack's 'pack_metadata.json' file's 'email' field is the empty string
    '''
    # Create all Necessary Temporary directories
    # create temp directory for the repo
    repo_dir = tmp_path / 'content_repo'
    repo_dir.mkdir()
    get_content_path_mock.return_value = repo_dir
    get_python_version_mock.return_value = 3.7
    # create temp target dir in which we will create all the TestSuite content items to use in the contribution zip and
    # that will be deleted after
    target_dir = repo_dir / 'target_dir'
    target_dir.mkdir()
    # create temp directory in which the contribution zip will reside
    contribution_zip_dir = tmp_path / 'contrib_zip'
    contribution_zip_dir.mkdir()
    # Create fake content repo and contribution zip
    repo = Repo(repo_dir)
    contrib_zip = Contribution(target_dir, 'ContribTestPack', repo)
    # contrib_zip.create_zip(contribution_zip_dir)
    contrib_zip.create_zip(contribution_zip_dir)

    # target_dir should have been deleted after creation of the zip file
    assert not target_dir.exists()

    name = 'Test Pack'
    contribution_path = contrib_zip.created_zip_filepath
    description = 'test pack description here'
    author = 'Octocat Smith'
    gh_user = 'octocat'
    contrib_converter_inst = ContributionConverter(
        name=name, contribution=contribution_path, description=description, author=author, gh_user=gh_user,
        no_pipenv=True)
    contrib_converter_inst.convert_contribution_to_pack()

    converted_pack_path = repo_dir / 'Packs' / 'TestPack'
    assert converted_pack_path.exists()

    pack_metadata_path = converted_pack_path / 'pack_metadata.json'
    assert pack_metadata_path.exists()
    with open(pack_metadata_path, 'r') as pack_metadata:
        metadata = json.load(pack_metadata)
        assert metadata.get('name', '') == name
        assert metadata.get('description', '') == description
        assert metadata.get('author', '') == author
        assert metadata.get('githubUser', []) == [gh_user]
        assert not metadata.get('email')


@pytest.mark.parametrize('input_name,expected_output_name', name_reformatting_test_examples)
def test_format_pack_dir_name(contrib_converter, input_name, expected_output_name):
    '''Test the 'format_pack_dir_name' method with various inputs

    Args:
        contrib_converter (fixture): An instance of the ContributionConverter class
        input_name (str): A 'name' argument value to test
        expected_output_name (str): The value expected to be returned by passing 'input_name'
            to the 'format_pack_dir_name' method

    Scenario: Creating a new pack from a contribution zip file

    Given
    - A pack name

    When
    - The pack name is passed to the 'format_pack_dir_name' method

    Then
    - Ensure the reformatted pack name returned by the method matches the expected output
    - Ensure the reformatted pack name returned by the method contains only valid characters
        (alphanumeric, underscore, and dash with no whitespace)
    '''
    output_name = contrib_converter.format_pack_dir_name(input_name)
    assert output_name == expected_output_name
    assert not re.search(
        r'\s', output_name), 'Whitespace was found in the returned value from executing "format_pack_dir_name"'
    err_msg = 'Characters other than alphanumeric, underscore, and dash were found in the output'
    assert all([char.isalnum() or char in {'_', '-'} for char in output_name]), err_msg
    if len(output_name) > 1:
        first_char = output_name[0]
        if first_char.isalpha():
            assert first_char.isupper(), 'The output\'s first character should be capitalized'
    assert not output_name.startswith(('-', '_')), 'The output\'s first character must be alphanumeric'
    assert not output_name.endswith(('-', '_')), 'The output\'s last character must be alphanumeric'


def test_convert_contribution_dir_to_pack_contents(tmp_path):
    """
    Scenario: convert a directory which was unarchived from a contribution zip into the content
        pack directory into which the contribution is intended to update, and the contribution
        includes a file that already exists in the pack

    Given
    - The pack's original content contains incident field files and appears like so

        ├── IncidentFields
        │   └── incidentfield-SomeIncidentField.json

    When
    - After the contribution zip files have been unarchived to the destination pack the pack
        directory tree appears like so

        ├── IncidentFields
        │   └── incidentfield-SomeIncidentField.json
        ├── incidentfield
        │   └── incidentfield-SomeIncidentField.json

    Then
    - Ensure the file '.../incidentfield/incidentfield-SomeIncidentField.json' is moved to
        '.../IncidentFields/incidentfield-SomeIncidentField.json' and overwrites the existing file
    """
    fake_pack_subdir = tmp_path / 'IncidentFields'
    fake_pack_subdir.mkdir()
    extant_file = fake_pack_subdir / 'incidentfield-SomeIncidentField.json'
    old_json = {"field": "old_value"}
    extant_file.write_text(json.dumps(old_json))
    fake_pack_extracted_dir = tmp_path / 'incidentfield'
    fake_pack_extracted_dir.mkdir()
    update_file = fake_pack_extracted_dir / 'incidentfield-SomeIncidentField.json'
    new_json = {"field": "new_value"}
    update_file.write_text(json.dumps(new_json))
    cc = ContributionConverter()
    cc.pack_dir_path = tmp_path
    cc.convert_contribution_dir_to_pack_contents(fake_pack_extracted_dir)
    assert json.loads(extant_file.read_text()) == new_json
    assert not fake_pack_extracted_dir.exists()


def test_convert_contribution_dir_to_pack_contents_update_mapper(tmp_path):
    """
    Scenario: convert a directory which was unarchived from a contribution zip into the content
        pack directory into which the contribution is intended to update, and the contribution
        includes a file that already exists in the pack

    Given
    - The pack's original content contains mapper files and appears like so

        ├── Classifiers
        │   └── classifier-mapper-MyMapper.json

    When
    - After the contribution zip files have been unarchived to the destination pack the pack
        directory tree appears like so

        ├── classifier
        │   └── classifier-MyMapper.json

    Then
    - Ensure the file '.../classifier/classifier-MyMapper.json' is moved to
        '.../Classifiers/classifier-mapper-MyMapper.json' and overwrites the existing file.
    """
    fake_pack_subdir = tmp_path / 'Classifiers'
    fake_pack_subdir.mkdir()
    extant_file = fake_pack_subdir / 'classifier-mapper-MyMapper.json'
    old_json = {"mapping": "old_value", "type": "mapping-incoming"}
    extant_file.write_text(json.dumps(old_json))
    fake_pack_extracted_dir = tmp_path / 'classifier'
    fake_pack_extracted_dir.mkdir()
    update_file = fake_pack_extracted_dir / 'classifier-MyMapper.json'
    new_json = {"mapping": "new_value", "type": "mapping-incoming"}
    update_file.write_text(json.dumps(new_json))
    cc = ContributionConverter()
    cc.pack_dir_path = tmp_path
    cc.convert_contribution_dir_to_pack_contents(fake_pack_extracted_dir)
    assert json.loads(extant_file.read_text()) == new_json
    assert not fake_pack_extracted_dir.exists()


def test_convert_contribution_dir_to_pack_contents_new_mapper(tmp_path):
    """
    Scenario: convert a directory which was unarchived from a contribution zip into the content
        pack directory into which the contribution is intended to update, and the contribution
        includes a file that already exists in the pack

    Given
    - A new content pack contains mapper file

    When
    - After the contribution zip files have been unarchived to the destination pack the pack
        directory tree appears like so

        ├── classifier
        │   └── classifier-myMapper.json

    Then
    - Ensure the file '.../classifier/classifier-myMapper.json' is moved to
        '.../Classifiers/classifier-mapper-myMapper.json' and overwrites the existing file.
    """

    fake_pack_extracted_dir = tmp_path / 'classifier'
    fake_pack_extracted_dir.mkdir()
    update_file = fake_pack_extracted_dir / 'classifier-myMapper.json'
    json_data = {"mapping": "new_value", "type": "mapping-incoming"}
    update_file.write_text(json.dumps(json_data))
    extant_file = tmp_path / 'Classifiers' / 'classifier-mapper-myMapper.json'
    cc = ContributionConverter()
    cc.pack_dir_path = tmp_path
    cc.convert_contribution_dir_to_pack_contents(fake_pack_extracted_dir)
    assert json.loads(extant_file.read_text()) == json_data
    assert not fake_pack_extracted_dir.exists()


def test_convert_contribution_dir_to_pack_contents_new_indicatorfield(tmp_path):
    """
    Scenario: convert a directory which was unarchived from a contribution zip into the content
        pack directory into which the contribution is intended to update, and the contribution
        includes a file that already exists in the pack

    Given
    - A new content pack contains indicatorfield file

    When
    - After the contribution zip files have been unarchived to the destination pack the pack
        directory tree appears like so

        ├── incidentfield
        │   └── indicatorfield-SomeIndicatorfieldField.json

    Then
    - Ensure the file '.../incidentfield/indicatorfield-SomeIndicatorfieldField.json' is moved to
        '.../IndicatorFields/indicatorfield-SomeIndicatorfieldField.json.json'.
    """
    fake_pack_extracted_dir = tmp_path / 'incidentfield'
    fake_pack_extracted_dir.mkdir()
    update_file = fake_pack_extracted_dir / 'indicatorfield-SomeIncidentField.json'
    json_data = {"field": "new_value"}
    update_file.write_text(json.dumps(json_data))
    extant_file = tmp_path / 'IndicatorFields' / 'indicatorfield-SomeIncidentField.json'
    cc = ContributionConverter()
    cc.pack_dir_path = tmp_path
    cc.convert_contribution_dir_to_pack_contents(fake_pack_extracted_dir)
    assert not fake_pack_extracted_dir.exists()
    assert json.loads(extant_file.read_text()) == json_data


def test_convert_contribution_dir_to_pack_contents_update_indicatorfield(tmp_path):
    """
    Scenario: convert a directory which was unarchived from a contribution zip into the content
        pack directory into which the contribution is intended to update, and the contribution
        includes a file that already exists in the pack

    Given
    - The pack's original content contains mapper files and appears like so

        ├── IndicatorFields
        │   └── indicatorfield-SomeIndicatorField.json

    When
    - After the contribution zip files have been unarchived to the destination pack the pack
        directory tree appears like so

        ├── incidentfield
        │   └── indicatorfield-SomeIndicatorField.json

    Then
    - Ensure the file '.../incidentfield/indicatorfield-SomeIndicatorField.json' is moved to
        '.../IndicatorFields/indicatorfield-SomeIndicatorField.json' and overwrites the existing file.
    """
    fake_pack_subdir = tmp_path / 'IndicatorFields'
    fake_pack_subdir.mkdir()
    extant_file = fake_pack_subdir / 'indicatorfield-SomeIndicatorField.json'
    old_json = {"field": "old_value"}
    extant_file.write_text(json.dumps(old_json))
    fake_pack_extracted_dir = tmp_path / 'incidentfield'
    fake_pack_extracted_dir.mkdir()
    update_file = fake_pack_extracted_dir / 'indicatorfield-SomeIndicatorField.json'
    new_json = {"field": "new_value"}
    update_file.write_text(json.dumps(new_json))
    cc = ContributionConverter()
    cc.pack_dir_path = tmp_path
    cc.convert_contribution_dir_to_pack_contents(fake_pack_extracted_dir)
    assert json.loads(extant_file.read_text()) == new_json
    assert not fake_pack_extracted_dir.exists()


@pytest.mark.parametrize('contribution_converter', ['TestPack'], indirect=True)
class TestEnsureUniquePackDirName:
    def test_ensure_unique_pack_dir_name_no_conflict(self, contribution_converter):
        """Test the 'ensure_unique_pack_dir_name' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Creating a new pack from a contribution zip file

        Given
        - A pack's directory name

        When
        - The pack's proposed directory name is passed to the 'ensure_unique_pack_dir_name' method
        - There does not already exist a pack directory with the proposed name

        Then
        - Ensure the pack directory name returned by the method matches the expected output - should be unchanged
        """
        pack_name = 'TestPack'
        crb_crvrt = contribution_converter
        assert crb_crvrt.name == pack_name
        assert crb_crvrt.dir_name == pack_name
        print(f'crb_crvrt.pack_dir_path={crb_crvrt.pack_dir_path}')
        assert os.path.isdir(crb_crvrt.pack_dir_path)

    def test_ensure_unique_pack_dir_name_with_conflict(self, contribution_converter):
        """Test the 'ensure_unique_pack_dir_name' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Creating a new pack from a contribution zip file

        Given
        - A pack's directory name

        When
        - The pack's proposed directory name is passed to the 'ensure_unique_pack_dir_name' method
        - There already exists a pack directory with the proposed name

        Then
        - Ensure the pack directory name returned by the method matches the expected output, which is that a
          version number should have been added
        """
        pack_name = 'TestPack'
        crb_crvrt = contribution_converter
        assert crb_crvrt.name == pack_name
        assert crb_crvrt.dir_name == pack_name
        assert os.path.isdir(crb_crvrt.pack_dir_path)
        new_pack_dir_name = crb_crvrt.ensure_unique_pack_dir_name(pack_name)
        assert new_pack_dir_name != pack_name
        assert new_pack_dir_name == pack_name + 'V2'

    def mock_format_manager(*args):
        return args

    @pytest.mark.parametrize('new_pack', [True, False])
    def test_format_converted_pack(self, contribution_converter, mocker, new_pack):
        """Test the 'format_converted_pack' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Formatting the added/modified files by checking against "xsoar-contrib/master" repo

        Given
        - ContributionConverter class

        When
        - Running the format_converted_pack method to format the files

        Then
        - Ensure the repo we are comparing with is "xsoar-contrib/master"
        """
        contribution_converter.create_new = new_pack
        result = mocker.patch('demisto_sdk.commands.init.contribution_converter.format_manager',
                              side_efect=self.mock_format_manager())
        contribution_converter.format_converted_pack()

        assert result.call_args[1].get('prev_ver') == 'xsoar-contrib/master'

    def test_ensure_unique_pack_dir_name_with_conflict_and_version_suffix(self, contribution_converter):
        """Test the 'ensure_unique_pack_dir_name' method

        Args:
            contribution_converter (fixture): An instance of the ContributionConverter class

        Scenario: Creating a new pack from a contribution zip file

        Given
        - A pack's directory name

        When
        - The pack's proposed directory name is passed to the 'ensure_unique_pack_dir_name' method
        - There already exists a pack directory with the proposed name
        - The proposed name ends with a version suffix, e.g. 'V2'

        Then
        - Ensure the pack directory name returned by the method matches the expected output, which is that the
          version number should have been incremented
        """
        pack_name = 'TestPack'
        crb_crvrt = contribution_converter
        assert crb_crvrt.name == pack_name
        assert crb_crvrt.dir_name == pack_name
        assert os.path.isdir(crb_crvrt.pack_dir_path)
        new_pack_dir_name = crb_crvrt.ensure_unique_pack_dir_name(pack_name)
        assert new_pack_dir_name != pack_name
        assert new_pack_dir_name == pack_name + 'V2'
        os.makedirs(os.path.join(crb_crvrt.packs_dir_path, new_pack_dir_name))
        incremented_new_pack_dir_name = crb_crvrt.ensure_unique_pack_dir_name(new_pack_dir_name)
        assert incremented_new_pack_dir_name == pack_name + 'V3'


class TestReleaseNotes:
    @pytest.fixture(autouse=True)
    def rn_file_copy(self):
        yield shutil.copyfile(SOURCE_RELEASE_NOTES_FILE, RELEASE_NOTES_COPY)
        if os.path.exists(RELEASE_NOTES_COPY):
            os.remove(RELEASE_NOTES_COPY)

    def test_replace_RN_template_with_value(self, mocker, contrib_converter, rn_file_copy):
        """Test the 'replace_RN_template_with_value' method
        Scenario:
            Adding the user's release note text to the rn file that was generated by the UpdateRN class.
            Detected content item has less object than git detected.

        Given
        - A pack's release note file path

        When
        - The contribution was made to an existing pack.

        Then
        - Ensure the RN file template text was modified with the user's input
        """
        contrib_converter.release_notes = "#### Integrations\n##### CrowdStrikeMalquery\n- release note entry number " \
                                          "#1\n- release note entry number #2\n\n#### Playbooks\n##### " \
                                          "CrowdStrikeMalquery - Multidownload and Fetch\n- changed this playbook\n- " \
                                          "Updated another thing\n\n"
        contrib_converter.detected_content_items = [
            {
                "id": "CrowdStrikeMalquery_copy",
                "name": "CrowdStrikeMalquery_copy",
                "source_id": "CrowdStrikeMalquery",
                "source_name": "CrowdStrikeMalquery",
                "source_file_name": "Packs/CrowdStrikeMalquery/Integrations/CrowdStrikeMalquery/CrowdStrikeMalquery.yml"
            }
        ]

        mocker.patch.object(UpdateRN, 'get_display_name', return_value='CrowdStrike Malquery')
        contrib_converter.replace_RN_template_with_value(RELEASE_NOTES_COPY)

        assert util_open_file(RELEASE_NOTES_COPY) == util_open_file(EXPECTED_RELEASE_NOTES)
        assert True

    def test_format_user_input(self, mocker, contrib_converter, rn_file_copy):
        """Test the 'format_user_input' method
        Given
        - A pack's release note file path

        When
        - The contribution was made to an existing pack.

        Then
        - Ensure the dictionary being built contains the relevant data with the content item display name if exists.
        """
        contrib_converter.release_notes = "#### Integrations\n##### CrowdStrikeMalquery\n- release note entry number " \
                                          "#1\n- release note entry number #2\n\n#### Playbooks\n##### " \
                                          "CrowdStrikeMalquery - Multidownload and Fetch\n- changed this playbook\n- " \
                                          "Updated another thing\n\n"
        contrib_converter.detected_content_items = [
            {"id": "a8026480-a286-46c7-8c44-b5161a37009d",
             "name": "CrowdStrikeMalquery - Multidownload and Fetch_copy",
             "source_id": "CrowdStrikeMalquery - Multidownload and Fetch",
             "source_name": "CrowdStrikeMalquery - Multidownload and Fetch",
             "source_file_name": "Packs/CrowdStrikeMalquery/Playbooks/CrowdStrikeMalquery_-_GenericPolling_"
                                 "-_Multidownload_and_Fetch.yml"},
            {"id": "CrowdStrikeMalquery_copy",
             "name": "CrowdStrikeMalquery_copy",
             "source_id": "CrowdStrikeMalquery",
             "source_name": "CrowdStrikeMalquery",
             "source_file_name": "Packs/CrowdStrikeMalquery/Integrations/CrowdStrikeMalquery/CrowdStrikeMalquery.yml"}]
        expected_rn_per_content_item = {'CrowdStrike Malquery':
                                        '- release note entry number #1\n- release note entry number #2\n',
                                        'CrowdStrikeMalquery - Multidownload and Fetch':
                                            '- changed this playbook\n- Updated another thing\n'}
        mocker.patch.object(
            UpdateRN, 'get_display_name',
            side_effect=['CrowdStrike Malquery', 'CrowdStrikeMalquery - Multidownload and Fetch'])
        rn_per_content_item = contrib_converter.format_user_input()
        assert expected_rn_per_content_item == rn_per_content_item

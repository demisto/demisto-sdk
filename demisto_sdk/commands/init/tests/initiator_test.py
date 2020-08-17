import json
import os
import re
from collections import OrderedDict, deque
from datetime import datetime
from os import listdir
from pathlib import Path
from typing import Callable

import pytest
import yaml
import yamlordereddictloader
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (INTEGRATION_CATEGORIES,
                                                   PACK_INITIAL_VERSION,
                                                   PACK_SUPPORT_OPTIONS,
                                                   XSOAR_AUTHOR, XSOAR_SUPPORT,
                                                   XSOAR_SUPPORT_URL)
from demisto_sdk.commands.init.initiator import Initiator
from mock import patch
from TestSuite.contribution import Contribution
from TestSuite.repo import Repo

DIR_NAME = 'DirName'
PACK_NAME = 'PackName'
PACK_DESC = 'PackDesc'
PACK_SERVER_MIN_VERSION = '5.5.0'
PACK_AUTHOR = 'PackAuthor'
PACK_URL = 'https://www.github.com/pack'
PACK_EMAIL = 'author@mail.com'
PACK_TAGS = 'Tag1,Tag2'
PACK_GITHUB_USERS = ''
INTEGRATION_NAME = 'IntegrationName'
SCRIPT_NAME = 'ScriptName'

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


@pytest.fixture
def initiator():
    return Initiator('')


def generate_multiple_inputs(inputs: deque) -> Callable:
    def next_input(_):
        return inputs.popleft()

    return next_input


def raise_file_exists_error():
    raise FileExistsError


def test_get_created_dir_name(monkeypatch, initiator):
    monkeypatch.setattr('builtins.input', lambda _: DIR_NAME)
    initiator.get_created_dir_name('integration')
    assert initiator.dir_name == DIR_NAME


def test_get_object_id(monkeypatch, initiator):
    initiator.dir_name = DIR_NAME
    # test integration object with ID like dir name
    monkeypatch.setattr('builtins.input', lambda _: 'Y')
    initiator.get_object_id('integration')
    assert initiator.id == DIR_NAME

    initiator.id = ''
    # test pack object with ID like dir name
    monkeypatch.setattr('builtins.input', lambda _: 'Y')
    initiator.get_object_id('pack')
    assert initiator.id == DIR_NAME

    initiator.id = ''
    # test script object with ID different than dir name
    monkeypatch.setattr('builtins.input', generate_multiple_inputs(deque(['N', 'SomeIntegrationID'])))
    initiator.get_object_id('script')
    assert initiator.id == 'SomeIntegrationID'


def test_get_object_id_custom_name(monkeypatch, initiator):
    """Tests integration with custom name of id
    """
    given_id = 'given_id'
    monkeypatch.setattr('builtins.input', lambda _: given_id)
    initiator.is_pack_creation = False
    initiator.get_object_id('integration')
    assert given_id == initiator.id


def test_create_metadata(monkeypatch, initiator):
    # test create_metadata without user filling manually
    pack_metadata = initiator.create_metadata(False)
    assert pack_metadata == {
        'name': '## FILL MANDATORY FIELD ##',
        'description': '## FILL MANDATORY FIELD ##',
        'support': XSOAR_SUPPORT,
        'currentVersion': PACK_INITIAL_VERSION,
        'author': XSOAR_AUTHOR,
        'url': XSOAR_SUPPORT_URL,
        'email': '',
        'created': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
        'categories': [],
        'tags': [],
        'useCases': [],
        'keywords': []
    }

    # test create_metadata with user filling manually
    monkeypatch.setattr(
        'builtins.input',
        generate_multiple_inputs(
            deque([
                PACK_NAME, PACK_DESC, '2', '1', PACK_AUTHOR,
                PACK_URL, PACK_EMAIL, PACK_TAGS, PACK_GITHUB_USERS
            ])
        )
    )
    pack_metadata = initiator.create_metadata(True)
    assert pack_metadata == {
        'author': PACK_AUTHOR,
        'categories': [INTEGRATION_CATEGORIES[0]],
        'currentVersion': '1.0.0',
        'description': PACK_DESC,
        'email': PACK_EMAIL,
        'keywords': [],
        'name': PACK_NAME,
        'support': PACK_SUPPORT_OPTIONS[1],
        'tags': ['Tag1', 'Tag2'],
        'created': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
        'url': PACK_URL,
        'useCases': [],
        'githubUser': []
    }


def test_get_valid_user_input(monkeypatch, initiator):
    monkeypatch.setattr('builtins.input', generate_multiple_inputs(deque(['InvalidInput', '100', '1'])))
    user_choice = initiator.get_valid_user_input(INTEGRATION_CATEGORIES, 'Choose category')
    assert user_choice == INTEGRATION_CATEGORIES[0]


def test_create_new_directory(mocker, monkeypatch, initiator):
    full_output_path = 'path'
    initiator.full_output_path = full_output_path

    # create new dir successfully
    mocker.patch.object(os, 'mkdir', return_value=None)
    assert initiator.create_new_directory()

    mocker.patch.object(os, 'mkdir', side_effect=FileExistsError)
    # override dir successfully
    monkeypatch.setattr('builtins.input', lambda _: 'Y')
    with pytest.raises(FileExistsError):
        assert initiator.create_new_directory()

    # fail to create pack cause of existing dir without overriding it
    monkeypatch.setattr('builtins.input', lambda _: 'N')
    assert initiator.create_new_directory() is False


def test_yml_reformatting(tmp_path, initiator):
    integration_id = 'HelloWorld'
    initiator.id = integration_id
    d = tmp_path / integration_id
    d.mkdir()
    full_output_path = Path(d)
    initiator.full_output_path = full_output_path

    p = d / f'{integration_id}.yml'
    with p.open(mode='w') as f:
        yaml.dump(
            {
                'commonfields': {
                    'id': ''
                },
                'name': '',
                'display': ''
            },
            f
        )
    dir_name = 'HelloWorldTest'
    initiator.dir_name = dir_name
    initiator.yml_reformatting(current_suffix=initiator.HELLO_WORLD_INTEGRATION, integration=True)
    with open(full_output_path / f'{dir_name}.yml', 'r') as f:
        yml_dict = yaml.load(f, Loader=yamlordereddictloader.SafeLoader)
        assert yml_dict == OrderedDict({
            'commonfields': OrderedDict({
                'id': 'HelloWorld'
            }),
            'display': 'HelloWorld',
            'name': 'HelloWorld'
        })


@patch('demisto_sdk.commands.split_yml.extractor.get_python_version')
@patch('demisto_sdk.commands.init.initiator.get_content_path')
def test_convert_contribution_zip(get_content_path_mock, get_python_version_mock, tmp_path, initiator):
    '''Create a fake contribution zip file and test that it is converted to a Pack correctly

    Args:
        get_content_path_mock (MagicMock): Patch of the 'get_content_path' function to return the fake repo directory
            used in the test
        get_python_version_mock (MagicMock): Patch of the 'get_python_version' function to return the "3.7"
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards
        initiator (fixture): Initializes an instance of the 'Initiator' class

    Scenario: Simulate executing the 'init' command with the 'contribution' option passed

    Given
    - A contribution zip file
    - The zipfile contains a unified script file
    - The zipfile contains a unified integration file
    When
    - Converting the zipfile to a valid Pack structure
    Then
    - Ensure script and integration are componentized and in valid directory structure
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

    initiator.contribution = contrib_zip.created_zip_filepath
    initiator.init()

    converted_pack_path = repo_dir / 'Packs' / 'ContribTestPack'
    assert converted_pack_path.exists()

    scripts_path = converted_pack_path / 'Scripts'
    sample_script_path = scripts_path / 'SampleScript'
    script_yml = sample_script_path / 'SampleScript.yml'
    script_py = sample_script_path / 'SampleScript.py'

    assert scripts_path.exists()
    assert sample_script_path.exists()
    assert script_yml.exists()
    assert script_py.exists()

    integrations_path = converted_pack_path / 'Integrations'
    sample_integration_path = integrations_path / 'Sample'
    integration_yml = sample_integration_path / 'Sample.yml'
    integration_py = sample_integration_path / 'Sample.py'
    integration_description = sample_integration_path / 'Sample_description.md'
    integration_image = sample_integration_path / 'Sample_image.png'
    integration_files = [integration_yml, integration_py, integration_description, integration_image]
    for integration_file in integration_files:
        assert integration_file.exists()


@patch('demisto_sdk.commands.split_yml.extractor.get_python_version')
@patch('demisto_sdk.commands.init.initiator.get_content_path')
def test_convert_contribution_zip_with_args(get_content_path_mock, get_python_version_mock, tmp_path):
    '''Convert a contribution zip to a pack and test that the converted pack's 'pack_metadata.json' is correct

    Args:
        get_content_path_mock (MagicMock): Patch of the 'get_content_path' function to return the fake repo directory
            used in the test
        get_python_version_mock (MagicMock): Patch of the 'get_python_version' function to return the "3.7"
        tmp_path (fixture): Temporary Path used for the unit test and cleaned up afterwards

    Scenario: Simulate executing the 'init' command with the 'contribution' option passed

    Given
    - A contribution zip file
    When
    - The initiator class instance is instantiated with the 'name' argument of 'Test Pack'
    - The initiator class instance is instantiated with the 'description' argument of 'test pack description here'
    - The initiator class instance is instantiated with the 'author' argument of 'Octocat Smith'
    Then
    - Ensure pack with directory name of 'TestPack' is created
    - Ensure that the pack's 'pack_metadata.json' file's 'name' field is 'Test Pack'
    - Ensure that the pack's 'pack_metadata.json' file's 'description' field is 'test pack description here'
    - Ensure that the pack's 'pack_metadata.json' file's 'author' field is 'Octocat Smith'
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
    initiator_inst = Initiator('', name=name, contribution=contribution_path, description=description, author=author)
    initiator_inst.init()

    converted_pack_path = repo_dir / 'Packs' / 'TestPack'
    assert converted_pack_path.exists()

    pack_metadata_path = converted_pack_path / 'pack_metadata.json'
    assert pack_metadata_path.exists()
    with open(pack_metadata_path, 'r') as pack_metadata:
        metadata = json.load(pack_metadata)
        assert metadata.get('name', '') == name
        assert metadata.get('description', '') == description
        assert metadata.get('author', '') == author
        assert not metadata.get('email')


@pytest.mark.parametrize('input_name,expected_output_name', name_reformatting_test_examples)
def test_format_pack_dir_name(initiator, input_name, expected_output_name):
    '''Test the 'format_pack_dir_name' method with various inputs

    Args:
        initiator (fixture): An instance of the Initiator class
        input_name (str): A 'name' argument value to test
        expected_output_name (str): The value expected to be returned by passing 'input_name'
            to the 'format_pack_dir_name' method

    Scenario: The demisto-sdk 'init' command is executed with the 'contribution' option

    Given
    - A pack name (taken from the contribution metadata or explicitly passed as a command option)

    When
    - The pack name is passed to the 'format_pack_dir_name' method

    Then
    - Ensure the reformatted pack name returned by the method matches the expected output
    - Ensure the reformatted pack name returned by the method contains only valid characters
        (alphanumeric, underscore, and dash with no whitespace)
    '''
    output_name = initiator.format_pack_dir_name(input_name)
    assert output_name == expected_output_name
    assert not re.search(r'\s',
                         output_name), 'Whitespace was found in the returned value from executing "format_pack_dir_name"'
    err_msg = 'Characters other than alphanumeric, underscore, and dash were found in the output'
    assert all([char.isalnum() or char in {'_', '-'} for char in output_name]), err_msg
    if len(output_name) > 1:
        first_char = output_name[0]
        if first_char.isalpha():
            assert first_char.isupper(), 'The output\'s first character should be capitalized'
    assert not output_name.startswith(('-', '_')), 'The output\'s first character must be alphanumeric'
    assert not output_name.endswith(('-', '_')), 'The output\'s last character must be alphanumeric'


def test_get_remote_templates__valid(mocker, initiator):
    """
    Tests get_remote_template function.
    Configures mocker instance and patches the tools's get_remote_file to return a file content.

    Given
        - A list of files to download from remote repo
    When
        - Initiating an object - Script or Integration
    Then
        - Ensure file with Test.py name was created in PackName folder
        - Ensure the file's content is the same as the one we got from get_remote_file return value
    """
    mocker.patch.object(tools, 'get_remote_file', return_value=b'Test im in file')
    initiator.full_output_path = PACK_NAME
    os.makedirs(PACK_NAME, exist_ok=True)
    res = initiator.get_remote_templates(['Test.py'])
    file_path = os.path.join(PACK_NAME, 'Test.py')
    with open(file_path, 'r') as f:
        file_content = f.read()

    assert res
    assert "Test im in file" in file_content

    os.remove(os.path.join(PACK_NAME, 'Test.py'))
    os.rmdir(PACK_NAME)


def test_get_remote_templates__invalid(mocker, initiator):
    """
    Tests get_remote_template function.
    Configures mocker instance and patches the tools's get_remote_file to return an empty file content.

    Given
        - An unreachable file to download from remote repo
    When
        - Initiating an object - Script or Integration
    Then
        - Ensure get_remote_templates returns False and doesn't raise an exception
    """
    mocker.patch.object(tools, 'get_remote_file', return_value={})
    initiator.full_output_path = PACK_NAME
    os.makedirs(PACK_NAME, exist_ok=True)
    res = initiator.get_remote_templates(['Test.py'])

    assert not res

    os.remove(os.path.join(PACK_NAME, 'Test.py'))
    os.rmdir(PACK_NAME)


def test_integration_init(initiator, tmpdir):
    """
    Tests `integration_init` function.

    Given
        - Inputs to init integration in a given output.

    When
        - Running the init command.

    Then
        - Ensure the function's return value is True
        - Ensure integration directory with the desired integration name is created successfully.
        - Ensure integration directory contain all files.
    """
    temp_pack_dir = os.path.join(tmpdir, PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)

    initiator.output = temp_pack_dir
    initiator.dir_name = INTEGRATION_NAME
    initiator.is_integration = True

    integration_path = os.path.join(temp_pack_dir, INTEGRATION_NAME)
    res = initiator.integration_init()
    integration_dir_files = {file for file in listdir(integration_path)}
    expected_files = {
        "Pipfile", "Pipfile.lock", f"{INTEGRATION_NAME}.py",
        f"{INTEGRATION_NAME}.yml", f"{INTEGRATION_NAME}_description.md", f"{INTEGRATION_NAME}_test.py",
        f"{INTEGRATION_NAME}_image.png", "test_data"
    }

    assert res
    assert os.path.isdir(integration_path)
    assert expected_files == integration_dir_files


def test_script_init(initiator, tmpdir):
    """
    Tests `script_init` function.

    Given
        - Inputs to init script in a given output.

    When
        - Running the init command.

    Then
        - Ensure the function's return value is True
        - Ensure script directory with the desired script name is created successfully.
        - Ensure script directory contain all files.
    """
    temp_pack_dir = os.path.join(tmpdir, PACK_NAME)
    os.makedirs(temp_pack_dir, exist_ok=True)

    initiator.dir_name = SCRIPT_NAME
    initiator.output = temp_pack_dir
    script_path = os.path.join(temp_pack_dir, SCRIPT_NAME)
    res = initiator.script_init()

    script_dir_files = {file for file in listdir(script_path)}

    assert res
    assert os.path.isdir(script_path)
    assert {f"{SCRIPT_NAME}.py", f"{SCRIPT_NAME}.yml", f"{SCRIPT_NAME}_test.py"} == script_dir_files

import os
import re
from collections import OrderedDict, deque
from datetime import datetime
from pathlib import Path
from typing import Callable

import pytest
import yaml
import yamlordereddictloader
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
                PACK_URL, PACK_EMAIL, PACK_TAGS
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
        'useCases': []
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

    mocker.patch.object(os, 'mkdir', side_effect=FileExistsError())
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
    assert not re.search(r'\s', output_name), 'Whitespace was found in the returned value from executing "format_pack_dir_name"'
    err_msg = 'Characters other than alphanumeric, underscore, and dash were found in the output'
    assert all([char.isalnum() or char in {'_', '-'} for char in output_name]), err_msg
    if len(output_name) > 1:
        first_char = output_name[0]
        if first_char.isalpha():
            assert first_char.isupper(), 'The output\'s first character should be capitalized'
    assert not output_name.startswith(('-', '_')), 'The output\'s first character must be alphanumeric'
    assert not output_name.endswith(('-', '_')), 'The output\'s last character must be alphanumeric'

import os
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

DIR_NAME = 'DirName'
PACK_NAME = 'PackName'
PACK_DESC = 'PackDesc'
PACK_SERVER_MIN_VERSION = '5.5.0'
PACK_AUTHOR = 'PackAuthor'
PACK_URL = 'https://www.github.com/pack'
PACK_EMAIL = 'author@mail.com'
PACK_TAGS = 'Tag1,Tag2'


# PACK_PRICE = '0'


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

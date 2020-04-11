from collections import deque
from datetime import datetime
from typing import Callable

import pytest
from demisto_sdk.commands.common.constants import (INTEGRATION_CATEGORIES,
                                                   PACK_INITIAL_VERSION,
                                                   PACK_SUPPORT_OPTIONS)
from demisto_sdk.commands.init.initiator import Initiator

DIR_NAME = 'DirName'
PACK_NAME = 'PackName'
PACK_DESC = 'PackDesc'
PACK_SERVER_MIN_VERSION = '5.5.0'
PACK_AUTHOR = 'PackAuthor'
PACK_URL = 'https://www.github.com/pack'
PACK_EMAIL = 'author@mail.com'
PACK_TAGS = 'Tag1,Tag2'
PACK_PRICE = '0'


@pytest.fixture
def initiator():
    return Initiator('')


def generate_multiple_inputs(inputs: deque) -> Callable:
    def next_input(_):
        return inputs.popleft()
    return next_input


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


def test_create_metadata(monkeypatch, initiator):
    # test create_metadata without user filling manually
    pack_metadata = initiator.create_metadata(False)
    assert pack_metadata == {
        'name': '## FILL OUT MANUALLY ##',
        'description': '## FILL OUT MANUALLY ##',
        'support': 'demisto',
        'serverMinVersion': '## FILL OUT MANUALLY #',
        'currentVersion': PACK_INITIAL_VERSION,
        'author': 'demisto',
        'url': 'https://www.demisto.com',
        'email': '',
        'categories': [],
        'tags': [],
        'created': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
        'updated': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
        'beta': False,
        'deprecated': False,
        'certification': 'certified',
        'useCases': [],
        'keywords': [],
        'price': '0',
        'dependencies': {},
    }

    # test create_metadata with user filling manually
    monkeypatch.setattr(
        'builtins.input',
        generate_multiple_inputs(
            deque([
                PACK_NAME, PACK_DESC, '1', PACK_SERVER_MIN_VERSION, PACK_AUTHOR,
                PACK_URL, PACK_EMAIL, '1', PACK_TAGS, PACK_PRICE
            ])
        )
    )
    pack_metadata = initiator.create_metadata(True)
    assert pack_metadata == {
        'author': PACK_AUTHOR,
        'beta': False,
        'categories': [INTEGRATION_CATEGORIES[0]],
        'certification': 'certified',
        'currentVersion': '1.0.0',
        'dependencies': {},
        'deprecated': False,
        'description': PACK_DESC,
        'email': PACK_EMAIL,
        'keywords': [],
        'name': PACK_NAME,
        'price': PACK_PRICE,
        'serverMinVersion': PACK_SERVER_MIN_VERSION,
        'support': PACK_SUPPORT_OPTIONS[0],
        'tags': ['Tag1', 'Tag2'],
        'created': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
        'updated': datetime.utcnow().strftime(Initiator.DATE_FORMAT),
        'url': PACK_URL,
        'useCases': []
    }

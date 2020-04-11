from collections import deque
from typing import Callable

import pytest
from demisto_sdk.commands.init.initiator import Initiator

DIR_NAME = 'DirName'


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

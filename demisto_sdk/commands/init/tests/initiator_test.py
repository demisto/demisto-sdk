import pytest
from demisto_sdk.commands.init.initiator import Initiator


@pytest.fixture
def initiator():
    return Initiator('')


def test_get_created_dir_name(monkeypatch, initiator):
    monkeypatch.setattr('builtins.input', lambda x: 'DirName')
    initiator.get_created_dir_name('integration')
    assert initiator.dir_name == 'DirName'

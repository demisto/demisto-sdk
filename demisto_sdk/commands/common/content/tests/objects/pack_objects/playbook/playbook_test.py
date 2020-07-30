from demisto_sdk.commands.common.content.content.objects.pack_objects import Playbook
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["playbook-Process_Email_-_Core.yml", "Process_Email_-_Core.yml"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Playbook)


@pytest.mark.parametrize(argnames="file", argvalues=["playbook-Process_Email_-_Core.yml", "Process_Email_-_Core.yml"])
def test_prefix(datadir, file: str):
    obj = Playbook(datadir[file])
    assert obj._normalized_file_name() == "playbook-Process_Email_-_Core.yml"

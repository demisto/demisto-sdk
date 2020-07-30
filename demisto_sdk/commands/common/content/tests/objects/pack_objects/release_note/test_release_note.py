from demisto_sdk.commands.common.content.content.objects.pack_objects import ReleaseNote
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["1_0_2.md", "1_0_3.md"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, ReleaseNote)


@pytest.mark.parametrize(argnames="file", argvalues=["1_0_2.md", "1_0_3.md"])
def test_prefix(datadir, file: str):
    obj = ReleaseNote(datadir[file])
    assert obj._normalized_file_name() == file

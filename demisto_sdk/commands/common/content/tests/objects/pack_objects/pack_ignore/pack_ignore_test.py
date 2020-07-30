from demisto_sdk.commands.common.content.content.objects.pack_objects import PackIgnore
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
import pytest


@pytest.mark.parametrize(argnames="file", argvalues=[".pack-ignore"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, PackIgnore)


@pytest.mark.parametrize(argnames="file", argvalues=[".pack-ignore"])
def test_prefix(datadir, file: str):
    obj = PackIgnore(datadir[file])
    assert obj._normalized_file_name() == ".pack-ignore"

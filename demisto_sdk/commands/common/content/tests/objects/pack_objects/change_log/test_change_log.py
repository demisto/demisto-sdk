from demisto_sdk.commands.common.content.content.objects.pack_objects import ChangeLog
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry


def test_objects_factory(datadir):
    obj = ContentObjectFacotry.from_path(datadir['CHANGELOG.md'])
    assert isinstance(obj, ChangeLog)


def test_prefix(datadir):
    obj = ChangeLog(datadir['CHANGELOG.md'])
    assert obj._normalized_file_name() == 'CHANGELOG.md'

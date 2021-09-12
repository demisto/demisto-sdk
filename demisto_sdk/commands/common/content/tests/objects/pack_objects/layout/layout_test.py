import pytest

from demisto_sdk.commands.common.content.objects.pack_objects import \
    LayoutsContainer
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


class TestLayoutsContainer:
    @pytest.mark.parametrize(argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = path_to_pack_object(datadir[file])
        assert isinstance(obj, LayoutsContainer)

    @pytest.mark.parametrize(argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"])
    def test_prefix(self, datadir, file: str):
        obj = LayoutsContainer(datadir[file])
        assert obj.normalize_file_name() == "layoutscontainer-Zimperium_event.json"

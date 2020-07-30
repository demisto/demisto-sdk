from demisto_sdk.commands.common.constants import PACKS_DIR, LAYOUTS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import Layout, LayoutContainer
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
import pytest

from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
LAYOUT = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LAYOUTS_DIR / 'layout-sample_new.json'


class TestLayout:
    def test_objects_factory(self):
        obj = ContentObjectFacotry.from_path(LAYOUT)
        assert isinstance(obj, Layout)

    def test_prefix(self):
        obj = Layout(LAYOUT)
        assert obj._normalized_file_name() == LAYOUT.name


class TestLayoutContainer:
    @pytest.mark.parametrize(argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = ContentObjectFacotry.from_path(datadir[file])
        assert isinstance(obj, LayoutContainer)

    @pytest.mark.parametrize(argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"])
    def test_prefix(self, datadir, file: str):
        obj = LayoutContainer(datadir[file])
        assert obj._normalized_file_name() == "layoutscontainer-Zimperium_event.json"

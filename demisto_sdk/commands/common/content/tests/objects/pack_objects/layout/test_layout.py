from demisto_sdk.commands.common.content.content.objects.pack_objects import Layout, LayoutContainer
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
import pytest


class TestLayout:
    @pytest.mark.parametrize(argnames="file", argvalues=["layout-details-Zimperium_event.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = ContentObjectFacotry.from_path(datadir[file])
        assert isinstance(obj, Layout)

    @pytest.mark.parametrize(argnames="file", argvalues=["layout-details-Zimperium_event.json"])
    def test_prefix(self, datadir, file: str):
        obj = Layout(datadir[file])
        assert obj._normalized_file_name() == "layout-details-Zimperium_event.json"


class TestLayoutContainer:
    @pytest.mark.parametrize(argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = ContentObjectFacotry.from_path(datadir[file])
        assert isinstance(obj, LayoutContainer)

    @pytest.mark.parametrize(argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"])
    def test_prefix(self, datadir, file: str):
        obj = LayoutContainer(datadir[file])
        assert obj._normalized_file_name() == "layoutscontainer-Zimperium_event.json"

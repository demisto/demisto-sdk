import tempfile

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects import LayoutsContainer
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"


json = JSON_Handler()


class TestLayoutsContainer:
    @pytest.mark.parametrize(
        argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"]
    )
    def test_objects_factory(self, datadir, file: str):
        obj = path_to_pack_object(datadir[file])
        assert isinstance(obj, LayoutsContainer)

    @pytest.mark.parametrize(
        argnames="file", argvalues=["layoutscontainer-Zimperium_event.json"]
    )
    def test_prefix(self, datadir, file: str):
        obj = LayoutsContainer(datadir[file])
        assert obj.normalize_file_name() == "layoutscontainer-Zimperium_event.json"

    def test_unify(self):
        layout_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/layoutscontainer-test.json"
        with tempfile.TemporaryDirectory() as _dir:
            layouts_container_to_upload_path = LayoutsContainer(layout_path)._unify(
                _dir
            )[0]
            with open(str(layouts_container_to_upload_path)) as f:
                layouts_container_to_upload = json.load(f)
            assert "fromVersion" in layouts_container_to_upload
            assert "fromServerVersion" in layouts_container_to_upload
            assert "toVersion" in layouts_container_to_upload
            assert "toServerVersion" in layouts_container_to_upload

            assert (
                layouts_container_to_upload["fromVersion"]
                == layouts_container_to_upload["fromServerVersion"]
            )
            assert (
                layouts_container_to_upload["toVersion"]
                == layouts_container_to_upload["toServerVersion"]
            )

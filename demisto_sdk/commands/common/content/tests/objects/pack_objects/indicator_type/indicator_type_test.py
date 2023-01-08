import pytest

from demisto_sdk.commands.common.constants import INDICATOR_TYPES_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import (
    IndicatorType,
    OldIndicatorType,
)
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
INDICATOR_TYPE = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / INDICATOR_TYPES_DIR
    / "reputation-sample_new.json"
)


class TestIndicatorType:
    def test_objects_factory(self):
        obj = path_to_pack_object(INDICATOR_TYPE)
        assert isinstance(obj, IndicatorType)

    def test_prefix(self):
        obj = IndicatorType(INDICATOR_TYPE)
        assert obj.normalize_file_name() == INDICATOR_TYPE.name


class TestOldIndicatorType:
    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = path_to_pack_object(datadir[file])
        assert isinstance(obj, OldIndicatorType)

    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_prefix(self, datadir, file: str):
        obj = OldIndicatorType(datadir[file])
        assert obj.normalize_file_name() == "reputations.json"

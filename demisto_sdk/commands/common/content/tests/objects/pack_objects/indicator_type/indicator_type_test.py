from demisto_sdk.commands.common.content.content.objects.pack_objects import IndicatorType, OldIndicatorType
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.constants import INDICATOR_TYPES_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files

import pytest

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
INDICATOR_TYPE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / INDICATOR_TYPES_DIR / 'reputation-sample_new.json'


class TestIndicatorType:
    def test_objects_factory(self):
        obj = ContentObjectFacotry.from_path(INDICATOR_TYPE)
        assert isinstance(obj, IndicatorType)

    def test_prefix(self):
        obj = IndicatorType(INDICATOR_TYPE)
        assert obj._normalized_file_name() == INDICATOR_TYPE.name


class TestOldIndicatorType:
    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = ContentObjectFacotry.from_path(datadir[file])
        assert isinstance(obj, OldIndicatorType)

    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_prefix(self, datadir, file: str):
        obj = OldIndicatorType(datadir[file])
        assert obj._normalized_file_name() == "reputations.json"

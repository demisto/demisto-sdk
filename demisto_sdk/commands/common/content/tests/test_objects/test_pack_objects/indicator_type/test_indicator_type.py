from demisto_sdk.commands.common.content import IndicatorType, OldIndicatorType, ContentObjectFacotry

import pytest


class TestIndicatorType:
    @pytest.mark.parametrize(argnames="file", argvalues=["reputation-mitreAttck.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = ContentObjectFacotry.from_path(datadir[file])
        assert isinstance(obj, IndicatorType)

    @pytest.mark.parametrize(argnames="file", argvalues=["reputation-mitreAttck.json"])
    def test_prefix(self, datadir, file: str):
        obj = IndicatorType(datadir[file])
        assert obj._normalized_file_name() == "reputation-mitreAttck.json"


class TestOldIndicatorType:
    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_objects_factory(self, datadir, file: str):
        obj = ContentObjectFacotry.from_path(datadir[file])
        assert isinstance(obj, OldIndicatorType)

    @pytest.mark.parametrize(argnames="file", argvalues=["reputations.json"])
    def test_prefix(self, datadir, file: str):
        obj = OldIndicatorType(datadir[file])
        assert obj._normalized_file_name() == "reputations.json"

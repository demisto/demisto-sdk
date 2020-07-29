from demisto_sdk.commands.common.content import Dashboard, ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["dashboard-Home_4_0_0.json", "Home_4_0_0.json"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Dashboard)


@pytest.mark.parametrize(argnames="file", argvalues=["dashboard-Home_4_0_0.json", "Home_4_0_0.json"])
def test_prefix(datadir, file: str):
    obj = Dashboard(datadir[file])
    assert obj._normalized_file_name() == "dashboard-Home_4_0_0.json"

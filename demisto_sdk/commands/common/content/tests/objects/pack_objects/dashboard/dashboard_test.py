from demisto_sdk.commands.common.content.content.objects.pack_objects import Dashboard
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["dashboard-sample.json", "sample.json"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Dashboard)


@pytest.mark.parametrize(argnames="file", argvalues=["dashboard-sample.json", "sample.json"])
def test_prefix(datadir, file: str):
    obj = Dashboard(datadir[file])
    assert obj._normalized_file_name() == "dashboard-sample.json"

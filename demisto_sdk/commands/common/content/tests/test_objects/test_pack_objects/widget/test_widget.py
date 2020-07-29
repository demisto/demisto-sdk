from demisto_sdk.commands.common.content import Widget, ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["widget-OnCallHoursPerUser.json", "OnCallHoursPerUser.json"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Widget)


@pytest.mark.parametrize(argnames="file", argvalues=["widget-OnCallHoursPerUser.json", "OnCallHoursPerUser.json"])
def test_prefix(datadir, file: str):
    obj = Widget(datadir[file])
    assert obj._normalized_file_name() == "widget-OnCallHoursPerUser.json"

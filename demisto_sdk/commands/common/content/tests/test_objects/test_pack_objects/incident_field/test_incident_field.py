from demisto_sdk.commands.common.content import IncidentField, ContentObjectFacotry

import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["Claroty_Category.json", "incidentfield-Claroty_Category.json"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, IncidentField)


@pytest.mark.parametrize(argnames="file", argvalues=["Claroty_Category.json", "incidentfield-Claroty_Category.json"])
def test_prefix(datadir, file: str):
    obj = IncidentField(datadir[file])
    assert obj._normalized_file_name() == "incidentfield-Claroty_Category.json"

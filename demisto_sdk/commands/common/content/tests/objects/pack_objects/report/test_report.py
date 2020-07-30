from demisto_sdk.commands.common.content.content.objects.pack_objects import Report
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["report-last24HoursClosedIncidentsReport.json",
                                                     "last24HoursClosedIncidentsReport.json"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, Report)


@pytest.mark.parametrize(argnames="file", argvalues=["report-last24HoursClosedIncidentsReport.json",
                                                     "last24HoursClosedIncidentsReport.json"])
def test_prefix(datadir, file: str):
    obj = Report(datadir[file])
    assert obj._normalized_file_name() == "report-last24HoursClosedIncidentsReport.json"

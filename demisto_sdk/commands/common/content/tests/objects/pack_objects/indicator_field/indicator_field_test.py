from demisto_sdk.commands.common.content.content.objects.pack_objects import IndicatorField
import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["incidentfield-sample.json"])
def test_prefix(datadir, file: str):
    obj = IndicatorField(datadir[file])
    assert obj._normalized_file_name() == "incidentfield-indicatorfield-sample.json"

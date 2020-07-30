from demisto_sdk.commands.common.content.content.objects.pack_objects import IncidentType
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
import pytest


@pytest.mark.parametrize(argnames="file", argvalues=["incidenttype-Prisma_Cloud_Compute_Audit.json"])
def test_objects_factory(datadir, file: str):
    obj = ContentObjectFacotry.from_path(datadir[file])
    assert isinstance(obj, IncidentType)


@pytest.mark.parametrize(argnames="file", argvalues=["incidenttype-Prisma_Cloud_Compute_Audit.json"])
def test_prefix(datadir, file: str):
    obj = IncidentType(datadir[file])
    assert obj._normalized_file_name() == "incidenttype-Prisma_Cloud_Compute_Audit.json"

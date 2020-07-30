from demisto_sdk.commands.common.content.content.objects.pack_objects import IncidentField
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.constants import INCIDENT_FIELDS_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
INCIDENT_FIELD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / INCIDENT_FIELDS_DIR / 'incidentfield-sample_new.json'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(INCIDENT_FIELD)
    assert isinstance(obj, IncidentField)


def test_prefix():
    obj = IncidentField(INCIDENT_FIELD)
    assert obj._normalized_file_name() == INCIDENT_FIELD.name

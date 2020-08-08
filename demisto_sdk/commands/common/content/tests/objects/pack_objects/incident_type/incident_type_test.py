from demisto_sdk.commands.common.content.content.objects.pack_objects import IncidentType
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.constants import INCIDENT_TYPES_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
INCIDENT_TYPE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / INCIDENT_TYPES_DIR / 'incidenttype-sample_new.json'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(INCIDENT_TYPE)
    assert isinstance(obj, IncidentType)


def test_prefix():
    obj = IncidentType(INCIDENT_TYPE)
    assert obj.normalized_file_name() == INCIDENT_TYPE.name

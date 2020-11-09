from demisto_sdk.commands.common.constants import INCIDENT_TYPES_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    IncidentType
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
INCIDENT_TYPE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / INCIDENT_TYPES_DIR / 'incidenttype-sample_new.json'


def test_objects_factory():
    obj = path_to_pack_object(INCIDENT_TYPE)
    assert isinstance(obj, IncidentType)


def test_prefix():
    obj = IncidentType(INCIDENT_TYPE)
    assert obj.normalize_file_name() == INCIDENT_TYPE.name

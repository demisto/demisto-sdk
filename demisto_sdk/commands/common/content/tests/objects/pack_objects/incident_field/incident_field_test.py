from demisto_sdk.commands.common.constants import INCIDENT_FIELDS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import IncidentField
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
INCIDENT_FIELD = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / INCIDENT_FIELDS_DIR
    / "incidentfield-sample_new.json"
)


def test_objects_factory():
    obj = path_to_pack_object(INCIDENT_FIELD)
    assert isinstance(obj, IncidentField)


def test_prefix():
    obj = IncidentField(INCIDENT_FIELD)
    assert obj.normalize_file_name() == INCIDENT_FIELD.name

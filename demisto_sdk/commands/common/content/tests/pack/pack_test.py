from pathlib import Path
import pytest

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.content import Pack
from demisto_sdk.commands.common.content.content.objects.pack_objects import (Integration, Script, Playbook,
                                                                              IncidentField,
                                                                              IncidentType, Classifier,
                                                                              Connection, IndicatorField, IndicatorType,
                                                                              Report, Dashboard, Layout,
                                                                              Widget, ReleaseNote, PackMetaData,
                                                                              SecretIgnore, Readme, ChangeLog,
                                                                              PackIgnore, Tool, DocFile)
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01'


@pytest.mark.parametrize(argnames="attribute, content_type, items",
                         argvalues=[
                             ('integrations', (Integration,), 3),
                             ('scripts', (Script,), 3),
                             ('classifiers', (Classifier,), 3),
                             ('playbooks', (Playbook,), 3),
                             ('incident_fields', (IncidentField,), 3),
                             ('incident_types', (IncidentType,), 3),
                             ('connections', (Connection,), 3),
                             ('indicator_fields', (IndicatorField,), 1),
                             ('indicator_types', (IndicatorType,), 3),
                             ('reports', (Report,), 3),
                             ('dashboards', (Dashboard,), 3),
                             ('layouts', (Layout,), 3),
                             ('widgets', (Widget,), 3),
                             ('release_notes', (ReleaseNote,), 1),
                             ('tools', (Tool,), 1),
                             ('doc_files', (DocFile,), 1),
                             ('test_playbooks', (Script, Playbook), 3),
                         ])
def test_generators_detection(attribute: str, content_type: tuple, items: int):
    pack = Pack(PACK)
    generator_as_list = list(pack.__getattribute__(attribute))
    # Check detect all objects
    assert len(generator_as_list) == items
    # Check all objects detected correctly
    for item in generator_as_list:
        assert isinstance(item, content_type)


@pytest.mark.parametrize(argnames="attribute, content_type",
                         argvalues=[
                             ('pack_ignore', PackIgnore),
                             ('changelog', ChangeLog),
                             ('readme', Readme),
                             ('pack_metadata', PackMetaData),
                             ('secrets_ignore', SecretIgnore),
                         ])
def test_detection(attribute: str, content_type: object):
    pack = Pack(PACK)
    assert isinstance(pack.__getattribute__(attribute), content_type)

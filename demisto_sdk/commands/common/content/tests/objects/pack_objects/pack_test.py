from typing import Tuple

import pytest
from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content import Pack
from demisto_sdk.commands.common.content.objects.pack_objects import (
    AgentTool, Classifier, Connection, Dashboard, DocFile, IncidentField,
    IncidentType, IndicatorField, IndicatorType, Integration, LayoutsContainer,
    PackIgnore, PackMetaData, Playbook, Readme, ReleaseNote, Report, Script,
    SecretIgnore, Widget)
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01'


@pytest.mark.parametrize(argnames="attribute, content_type, items",
                         argvalues=[
                             ('integrations', (Integration,), 3),
                             ('scripts', (Script,), 3),
                             ('classifiers', (Classifier,), 1),
                             ('playbooks', (Playbook,), 3),
                             ('incident_fields', (IncidentField,), 3),
                             ('incident_types', (IncidentType,), 3),
                             ('connections', (Connection,), 3),
                             ('indicator_fields', (IndicatorField,), 1),
                             ('indicator_types', (IndicatorType,), 3),
                             ('reports', (Report,), 3),
                             ('dashboards', (Dashboard,), 3),
                             ('layouts', (LayoutsContainer,), 3),
                             ('widgets', (Widget,), 3),
                             ('release_notes', (ReleaseNote,), 1),
                             ('tools', (AgentTool,), 1),
                             ('doc_files', (DocFile,), 1),
                             ('test_playbooks', (Script, Playbook), 2),
                         ])
def test_generators_detection(attribute: str, content_type: Tuple[type], items: int):
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
                             ('readme', Readme),
                             ('pack_metadata', PackMetaData),
                             ('secrets_ignore', SecretIgnore),
                         ])
def test_detection(attribute: str, content_type: type):
    pack = Pack(PACK)
    assert isinstance(pack.__getattribute__(attribute), content_type)

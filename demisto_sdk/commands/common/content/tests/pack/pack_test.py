from pathlib import Path
import pytest
from demisto_sdk.commands.common.content.content import Pack
from demisto_sdk.commands.common.content.content.objects.pack_objects import (Integration, Script, Playbook,
                                                                              IncidentField,
                                                                              IncidentType, Classifier,
                                                                              Connection, IndicatorField, IndicatorType,
                                                                              Report, Dashboard, Layout,
                                                                              Widget, ReleaseNote, PackMetaData,
                                                                              SecretIgnore, Readme, ChangeLog,
                                                                              PackIgnore, Tool, DocFile)


@pytest.mark.parametrize(argnames="attribute, content_type, items",
                         argvalues=[
                             ('integrations', (Integration,), 2),
                             ('scripts', (Script,), 1),
                             ('classifiers', (Classifier,), 1),
                             ('playbooks', (Playbook,), 1),
                             ('incident_fields', (IncidentField,), 1),
                             ('incident_types', (IncidentType,), 1),
                             ('connections', (Connection,), 1),
                             ('indicator_fields', (IndicatorField,), 1),
                             ('indicator_types', (IndicatorType,), 1),
                             ('reports', (Report,), 1),
                             ('dashboards', (Dashboard,), 1),
                             ('layouts', (Layout,), 1),
                             ('widgets', (Widget,), 1),
                             ('release_notes', (ReleaseNote,), 3),
                             ('tools', (Tool,), 1),
                             ('doc_files', (DocFile,), 1),
                             ('test_playbooks', (Script, Playbook), 2),
                         ])
def test_generators_detection(attribute: str, content_type: tuple, items: int):
    pack = Pack(Path(__file__).parent / 'test_pack')
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
    pack = Pack(Path(__file__).parent / 'test_pack')
    assert isinstance(pack.__getattribute__(attribute), content_type)

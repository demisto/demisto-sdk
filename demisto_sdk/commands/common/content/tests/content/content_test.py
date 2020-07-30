from pathlib import Path
import pytest
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.content.content.objects.content_objects import Documentation, ContentDescriptor
from demisto_sdk.commands.common.content.content.objects.pack_objects import Script, Playbook
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


@pytest.mark.parametrize(argnames="attribute, content_type, items",
                         argvalues=[
                             ('test_playbooks', (Script, Playbook), 3),
                             ('documentations', (Documentation,), 2)
                         ])
def test_generators_detection(attribute: str, content_type: tuple, items: int):
    pack = Content(TEST_CONTENT_REPO)
    generator_as_list = list(pack.__getattribute__(attribute))
    # Check detect all objects
    assert len(generator_as_list) == items
    # Check all objects detected correctly
    for item in generator_as_list:
        assert isinstance(item, content_type)


@pytest.mark.parametrize(argnames="attribute, content_type",
                         argvalues=[
                             ('content_descriptor', ContentDescriptor)
                         ])
def test_detection(attribute: str, content_type: object):
    pack = Content(TEST_CONTENT_REPO)
    assert isinstance(pack.__getattribute__(attribute), content_type)


def test_detect_all_docs():
    expected = ['doc-CommonServer.json', 'doc-howto.json']
    pack = Content(TEST_CONTENT_REPO)
    documentations = pack.documentations
    for doc in documentations:
        assert doc.path.name in expected

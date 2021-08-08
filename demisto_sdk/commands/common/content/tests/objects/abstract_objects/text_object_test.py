from pathlib import Path

import pytest

from demisto_sdk.commands.common.content.errors import ContentInitializeError
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_VALID_TEXT = TEST_CONTENT_REPO / 'Packs' / 'Sample01' / 'ReleaseNotes' / '1_1_1.md'


def test_valid_text_file_path():
    obj = TextObject(TEST_VALID_TEXT)
    assert obj.to_str() == Path(TEST_VALID_TEXT).read_text()


def test_malformed_text_path():
    with pytest.raises(ContentInitializeError):
        TextObject('Not valid path')

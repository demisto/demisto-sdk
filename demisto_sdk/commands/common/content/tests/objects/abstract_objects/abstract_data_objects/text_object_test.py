from pathlib import Path
import pytest

from demisto_sdk.commands.common.content.content.objects.abstract_objects import TextObject
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_VALID_TEXT = TEST_CONTENT_REPO / 'Packs' / 'Sample01' / 'ReleaseNotes' / '1_1_1.md'


def test_valid_yaml_file_path():
    obj = TextObject(TEST_VALID_TEXT)
    assert obj.to_str() == Path(TEST_VALID_TEXT).read_text()


def test_text_data_dir_path():
    obj = TextObject(TEST_VALID_TEXT)
    assert obj.to_str() == TEST_VALID_TEXT.read_text()


def test_malformed_text_path():
    with pytest.raises(BaseException) as excinfo:
        TextObject('Not valid path')

    assert "Unable to find text file in path" in str(excinfo)

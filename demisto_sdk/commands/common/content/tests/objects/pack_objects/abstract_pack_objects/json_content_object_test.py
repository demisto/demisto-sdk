from typing import Union

import pytest
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR, DEFAULT_CONTENT_ITEM_FROM_VERSION, PACKS_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TEST_JSON_NO_FROM_VERSION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CLASSIFIERS_DIR / 'classifier-sample_new.json'


def test_to_version_no_from_version(datadir):
    from packaging.version import parse
    obj = JSONContentObject(TEST_JSON_NO_FROM_VERSION, "classifier")
    assert obj.from_version == parse(DEFAULT_CONTENT_ITEM_FROM_VERSION)
    assert obj.to_version == parse("4.0.0")


TEST_LIST_JSON = TEST_CONTENT_REPO / "list_json.json"
TEST_NOT_LIST_JSON = TEST_CONTENT_REPO / "dict_json.json"
IS_LIST = [(TEST_LIST_JSON, '', True),
           (TEST_NOT_LIST_JSON, '', False)]


@pytest.mark.parametrize('path, file_name_prefix, is_list', IS_LIST)
def test_is_file_structure_list(path: Union[Path, str], file_name_prefix, is_list: bool):
    """
    Given
        - A json file path
    When
        - Checking if its content is a list of a dict
    Then
        - Returns true if the file's content is a list, else return false
    """
    assert JSONContentObject(path, file_name_prefix).is_file_structure_list() == is_list


class TestFileWithStem:
    def test_with_readme_change_log(self):
        obj = JSONContentObject(TEST_JSON_NO_FROM_VERSION, "classifier")

        assert obj.readme is not None
        assert obj.changelog is not None

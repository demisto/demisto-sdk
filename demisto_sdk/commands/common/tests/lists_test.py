import json

import pytest
from mock import patch

from demisto_sdk.commands.common.constants import LISTS_DIR, PACKS_DIR
from demisto_sdk.commands.common.hook_validations.lists import ListsValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
LIST_GOOD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'list-checked_integrations.json'
LIST_BAD_FROM_VERSION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'bad_from_version.json'
LIST_BAD_VERSION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'bad_version.json'
LIST_BAD_FORMAT = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'list-bad_format.json'


def mock_structure(file_path=None, current_file=None, old_file=None):
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'list'
        structure.file_path = file_path
        file = open(file_path, "r")
        structure.current_file = json.loads(file.read())
        file.close()
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        structure.quite_bc = False
        return structure


class TestListValidator:

    @pytest.mark.parametrize('list_path, is_valid', [
        (LIST_GOOD, True),
        (LIST_BAD_VERSION, False),
        (LIST_BAD_FROM_VERSION, False),
        (LIST_BAD_FORMAT, False)
    ])
    def test_is_valid_list(self, list_path, is_valid):
        """
        Given
        - A list with fromVersion of 6.5.0 and version of -1 OR A list with fromVersion of 1 and version of 1
        When
        - Validating a list
        Then
        - Return that the list is valid
        """
        structure = mock_structure(file_path=str(list_path))
        list_item = ListsValidator(structure, json_file_path=str(list_path))
        assert list_item.is_valid_list() == is_valid

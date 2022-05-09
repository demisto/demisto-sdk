from typing import Optional

import pytest
from mock import patch


from demisto_sdk.commands.common.hook_validations.test_playbook import \
    TestPlaybookValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator


def mock_structure(file_path=None, current_file=None, old_file=None):
    # type: (Optional[str], Optional[dict], Optional[dict]) -> StructureValidator
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'playbook'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        structure.specific_validations = None
        return structure


FROM_AND_TO_VERSION_FOR_TEST = [
    (
        {},
        True
    ),
    (
        {'fromversion': '0.0.0'},
        True
    ),
    (
        {'fromversion': '1.32.45'},
        True
    ),
    (
        {'toversion': '21.32.44'},
        True
    ),
    (
        {'toversion': '1.5'},
        False
    ),
    (
        {'toversion': '0.0.0', 'fromversion': '1.32.45'},
        True
    ),
    (
        {'toversion': '0.0.0', 'fromversion': '1.3_45'},
        False
    ),
    (
        {'toversion': '0.0.', 'fromversion': '1.32.45'},
        False
    ),
    (
        {'toversion': '0.f.0'},
        False
    ),

]


@pytest.mark.parametrize('current_file, expected_result',FROM_AND_TO_VERSION_FOR_TEST)
def test_are_fromversion_and_toversion_in_correct_format(current_file, expected_result):

    structure_validator = mock_structure('', current_file=current_file)
    test_playbook_validator = TestPlaybookValidator(structure_validator)
    assert test_playbook_validator.are_fromversion_and_toversion_in_correct_format() == expected_result

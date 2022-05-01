import pytest
from mock import patch

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.wizard import WizardValidator

json = JSON_Handler()


def get_validator(current_file=None, old_file=None, file_path=""):
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator("")
        structure.current_file = current_file
        structure.old_file = old_file
        structure.file_path = file_path
        structure.is_valid = True
        structure.prev_ver = 'master'
        structure.branch_name = ''
        structure.quiet_bc = False
        structure.specific_validations = None
        validator = WizardValidator(structure)
        validator.current_file = current_file
    return validator


class TestWizardValidator:
    @pytest.mark.parametrize('current_file, answer, id_set', [
        ({}, True, None),
        ({"dependency_packs": [{"packs": [{"name": "not_exists"}]}]}, False, {'Packs': {'exists': {}}}),
        ({"dependency_packs": [{"packs": [{"name": "exists"}]}]}, True, {'Packs': {'exists': {}}}),
        ({"dependency_packs": [{"packs": [{"name": "exists"}, {"name": "not_exists"}]}]}, False, {'Packs': {'exists': {}}}),
    ])
    def test_deleted_context_path(self, current_file, answer, id_set):
        """
            Given
            - A list with fromVersion of 6.5.0 and version of -1 OR A list with fromVersion of 1 and version of 1
            When
            - Validating a list
            Then
            - Return that the list is valid
        """
        validator = get_validator(current_file)
        assert validator.are_dependency_packs_valid(id_set) is answer

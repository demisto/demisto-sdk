import copy
from collections import namedtuple

from mock import patch

from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    GENERIC_FIELD


def mock_structure(file_path=None, current_file=None, old_file=None):
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'genericfield'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        structure.quite_bc = False
        structure.skip_schema_check = False
        structure.pykwalify_logs = False
        structure.scheme_name = namedtuple('scheme_name', 'value')(value='genericfield')
        structure.checked_files = set()
        structure.ignored_errors = dict()
        structure.suppress_print = True
        structure.json_file_path = None
        return structure


class TestGenericField:
    def test_simple_generic_field_is_fine(self, pack):
        field = pack.create_generic_field(pack.name, GENERIC_FIELD)
        structure = mock_structure(field.path, field.read_json_as_dict())
        assert structure.is_valid_scheme()

    def test_openended_removed(self, pack):
        generic_field = copy.deepcopy(GENERIC_FIELD)
        generic_field['openEnded'] = True
        field = pack.create_generic_field(pack.name, generic_field)
        structure = mock_structure(field.path, field.read_json_as_dict())
        assert structure.is_valid_scheme()

    def test_no_genericModuleId(self, pack):
        generic_field = copy.deepcopy(GENERIC_FIELD)
        del generic_field['genericModuleId']
        field = pack.create_generic_field(pack.name, generic_field)
        structure = mock_structure(field.path, field.read_json_as_dict())
        assert structure.is_valid_scheme() is False

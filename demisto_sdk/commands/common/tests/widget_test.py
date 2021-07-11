import pytest
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from mock import patch


def mock_structure(file_path=None, current_file=None, old_file=None, quite_bc=False):
    # type: (Optional[str], Optional[dict], Optional[dict]) -> StructureValidator
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'widget'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        structure.quite_bc = quite_bc
        return structure


@pytest.mark.parametrize('current_file, answer', [({'dataType': 'metrics', 'fromVersion': '6.2.0'}, True),
                                                  ({'dataType': 'metrics', 'fromVersion': '5.5.0'}, False),
                                                  ({'dataType': 'incidents', 'fromVersion': '6.2.0'}, True)])
def test_is_valid_fromversion(current_file, answer):
    """
    Given:
        A widget validator with dataType and fromVersion fields.

    When:
        Running is_valid_fromversion.

    Then:
        Ensure that the answer as expected.
    """
    structure = mock_structure()
    widget_validator = WidgetValidator(structure)

    widget_validator.current_file = current_file

    assert widget_validator._is_valid_fromversion() == answer

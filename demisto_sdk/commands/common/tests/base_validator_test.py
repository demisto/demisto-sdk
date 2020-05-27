import os

from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator

DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST = ['IN100', 'IN101', 'IN102', 'IN103', 'IN104', 'IN105', 'IN106', 'IN107',
                                         'IN108', 'IN109', 'IN110', 'IN111', 'IN112', 'IN113', 'IN114', 'IN115',
                                         'IN116', 'IN117', 'IN118', 'IN119', 'IN120', 'IN121', 'IN122', 'IN123',
                                         'IN124', 'SC100', 'DB100', 'DB101', 'DO100', 'DO101', 'DO102', 'DO103',
                                         'DO104', 'DO105', 'ID100', 'ID101', 'ID102', 'DA100', 'DA101', 'WD100',
                                         'WD101', 'IM100', 'IM101', 'IM102', 'IM103', 'IM104', 'IM105', 'IM106',
                                         'CJ100', 'CJ101', 'CJ102', 'CJ103', 'CJ104', 'RN100', 'RN101', 'RN102',
                                         'RN103', 'RN104', 'RN105', 'RN106', 'RN107', 'PB100', 'PB101', 'PB102',
                                         'PB103', 'DS100', 'DS101', 'DS102', 'DS103', 'IF100', 'IF101', 'IF102',
                                         'IF103', 'IF104', 'IF105', 'IF106', 'IF107', 'IF108', 'IF109', 'IF110',
                                         'IF111', 'IT100', 'PA100', 'PA101', 'PA102', 'PA103', 'PA104', 'PA105',
                                         'PA106', 'PA107', 'PA108', 'PA109', 'PA110', 'PA111', 'PA112', 'RM100',
                                         'RP100', 'RP101', 'RP102']


def test_handle_error():
    base_validator = BaseValidator(ignored_errors={'pack': ['SC101', 'SC103', "BA"], "file_name": {"IN100"}})
    formatted_error = base_validator.handle_error("Error-message", "SC102", "PATH")
    assert formatted_error == 'PATH: [SC102] - Error-message\n'

    formatted_error = base_validator.handle_error("ignore-this", "SC101", "PATH")
    assert formatted_error is None

    formatted_error = base_validator.handle_error("ignore-this-as-well", "BA100", "PATH")
    assert formatted_error is None

    formatted_error = base_validator.handle_error("another-error-message", "IN101", "path/to/file_name")
    assert formatted_error == 'path/to/file_name: [IN101] - another-error-message\n'

    formatted_error = base_validator.handle_error("ignore-file-specific", "IN100", "path/to/file_name")
    assert formatted_error is None


def test_check_deprecated_where_ignored_list_exists():
    files_path = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    test_file = os.path.join(files_path, 'DummyPack/Integrations/DummyDeprecatedIntegration/DummyDeprecatedIntegration.yml')
    base_validator = BaseValidator(ignored_errors={'DummyDeprecatedIntegration.yml': ['BA101']})
    base_validator.check_deprecated(test_file)
    assert base_validator.ignored_errors['DummyDeprecatedIntegration.yml'] == ["BA101"] + DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST


def test_check_deprecated_where_ignored_list_does_not_exist():
    files_path = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    test_file = os.path.join(files_path, 'DummyPack/Integrations/DummyDeprecatedIntegration/DummyDeprecatedIntegration.yml')
    base_validator = BaseValidator(ignored_errors={})
    base_validator.check_deprecated(test_file)
    assert base_validator.ignored_errors['DummyDeprecatedIntegration.yml'] == DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST

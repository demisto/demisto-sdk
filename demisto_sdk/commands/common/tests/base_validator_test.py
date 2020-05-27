import os

from demisto_sdk.commands.common.errors import PRESET_ERROR_TO_CHECK
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator

DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST = BaseValidator.create_reverse_ignored_errors_list(PRESET_ERROR_TO_CHECK['deprecated'])


def test_handle_error():
    base_validator = BaseValidator(ignored_errors={"file_name": ["BA101"]})
    formatted_error = base_validator.handle_error("Error-message", "SC102", "PATH")
    assert formatted_error == 'PATH: [SC102] - Error-message\n'

    formatted_error = base_validator.handle_error("another-error-message", "IN101", "path/to/file_name")
    assert formatted_error == 'path/to/file_name: [IN101] - another-error-message\n'

    formatted_error = base_validator.handle_error("ignore-file-specific", "BA101", "path/to/file_name")
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


def test_check_deprecated_non_deprecated_integration_no_ignored_errors():
    files_path = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    test_file = os.path.join(files_path, 'DummyPack/Integrations/DummyIntegration/DummyIntegration.yml')
    base_validator = BaseValidator(ignored_errors={})
    base_validator.check_deprecated(test_file)
    assert 'DummyIntegration' not in base_validator.ignored_errors


def test_check_deprecated_non_deprecated_integration_with_ignored_errors():
    files_path = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    test_file = os.path.join(files_path, 'DummyPack/Integrations/DummyIntegration/DummyIntegration.yml')
    base_validator = BaseValidator(ignored_errors={'DummyIntegration.yml': ["BA101"]})
    base_validator.check_deprecated(test_file)
    assert base_validator.ignored_errors['DummyIntegration.yml'] == ['BA101']


def test_check_deprecated_playbook():
    files_path = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    test_file = os.path.join(files_path, 'DummyPack/Playbooks/playbook-DummyDeprecatedPlaybook.yml')
    base_validator = BaseValidator(ignored_errors={})
    base_validator.check_deprecated(test_file)
    assert base_validator.ignored_errors['playbook-DummyDeprecatedPlaybook.yml'] == DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST

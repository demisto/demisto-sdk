from demisto_sdk.commands.common.constants import (PACK_METADATA_CERTIFICATION,
                                                   PACK_METADATA_SUPPORT)
from demisto_sdk.commands.common.errors import (FOUND_FILES_AND_ERRORS,
                                                FOUND_FILES_AND_IGNORED_ERRORS,
                                                PRESET_ERROR_TO_CHECK,
                                                PRESET_ERROR_TO_IGNORE)
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from TestSuite.test_tools import ChangeCWD

DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST = BaseValidator.create_reverse_ignored_errors_list(PRESET_ERROR_TO_CHECK['deprecated'])


def test_handle_error():
    """
    Given
    - An ignore errors list associated with a file.
    - An error, message, code and file paths.

    When
    - Running handle_error method.

    Then
    - Ensure the resulting error messages are correctly formatted.
    - Ensure ignored error codes return None.
    - Ensure non ignored errors are in FOUND_FILES_AND_ERRORS list.
    - Ensure ignored error are not in FOUND_FILES_AND_ERRORS and in FOUND_FILES_AND_IGNORED_ERRORS
    """
    base_validator = BaseValidator(ignored_errors={"file_name": ["BA101"]}, print_as_warnings=True)

    # passing the flag checks - checked separately
    base_validator.checked_files.union({'PATH', "file_name"})

    formatted_error = base_validator.handle_error("Error-message", "SC102", "PATH")
    assert formatted_error == 'PATH: [SC102] - Error-message\n'
    assert 'PATH - [SC102]' in FOUND_FILES_AND_ERRORS

    formatted_error = base_validator.handle_error("another-error-message", "IN101", "path/to/file_name")
    assert formatted_error == 'path/to/file_name: [IN101] - another-error-message\n'
    assert 'path/to/file_name - [IN101]' in FOUND_FILES_AND_ERRORS

    formatted_error = base_validator.handle_error("ignore-file-specific", "BA101", "path/to/file_name")
    assert formatted_error is None
    assert 'path/to/file_name - [BA101]' not in FOUND_FILES_AND_ERRORS
    assert 'path/to/file_name - [BA101]' in FOUND_FILES_AND_IGNORED_ERRORS

    formatted_error = base_validator.handle_error("Error-message", "ST109", "path/to/file_name")
    assert formatted_error == 'path/to/file_name: [ST109] - Error-message\n'
    assert 'path/to/file_name - [ST109]' in FOUND_FILES_AND_ERRORS


def test_check_deprecated_where_ignored_list_exists(repo):
    """
    Given
    - An deprecated integration yml.
    - A pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure the resulting ignored errors list included the existing errors as well as the deprecated default error list.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    integration.yml.write_dict({'deprecated': True})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={'integration.yml': ['BA101']})
        base_validator.check_deprecated(files_path)
    assert base_validator.ignored_errors['integration.yml'] == ["BA101"] + DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST


def test_check_deprecated_where_ignored_list_does_not_exist(repo):
    """
    Given
    - An deprecated integration yml.
    - No pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure the resulting ignored errors list included the deprecated default error list only.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    integration.yml.write_dict({'deprecated': True})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.check_deprecated(files_path)
    assert base_validator.ignored_errors['integration.yml'] == DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST


def test_check_deprecated_non_deprecated_integration_no_ignored_errors(repo):
    """
    Given
    - An non-deprecated integration yml.
    - No pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure there is no resulting ignored errors list.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    integration.yml.write_dict({'deprecated': False})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.check_deprecated(files_path)
    assert 'integration' not in base_validator.ignored_errors


def test_check_deprecated_non_deprecated_integration_with_ignored_errors(repo):
    """
    Given
    - An non-deprecated integration yml.
    - A pre-existing ignored errors list for the integration.

    When
    - Running check_deprecated method.

    Then
    - Ensure the resulting ignored errors list is the pre-existing one.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    integration.yml.write_dict({'deprecated': False})
    files_path = integration.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={'integration.yml': ["BA101"]})
        base_validator.check_deprecated(files_path)
    assert base_validator.ignored_errors['integration.yml'] == ['BA101']


def test_check_deprecated_playbook(repo):
    """
    Given
    - An non-deprecated playbook yml.

    When
    - Running check_deprecated method.

    Then
    - Ensure the resulting ignored errors list included the deprecated default error list only.
    """
    pack = repo.create_pack('pack')
    playbook = pack.create_integration('playbook-somePlaybook')
    playbook.yml.write_dict({'hidden': True})
    files_path = playbook.yml.path
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.check_deprecated(files_path)
    assert base_validator.ignored_errors['playbook-somePlaybook.yml'] == DEPRECATED_IGNORE_ERRORS_DEFAULT_LIST


def test_check_support_status_xsoar_file(repo, mocker):
    """
    Given
    - An xsoar supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the resulting ignored errors list does not include the integration file name.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    meta_json = {
        PACK_METADATA_SUPPORT: "xsoar",
        PACK_METADATA_CERTIFICATION: "certified"
    }
    mocker.patch.object(BaseValidator, 'get_metadata_file_content', return_value=meta_json)
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml_path)

        assert 'integration.yml' not in base_validator.ignored_errors


def test_check_support_status_non_certified_partner_file(repo, mocker):
    """
    Given
    - An non-certified partner supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the resulting ignored errors list includes the non-certified-partner ignore-list.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    meta_json = {
        PACK_METADATA_SUPPORT: "partner",
        PACK_METADATA_CERTIFICATION: "not certified"
    }
    mocker.patch.object(BaseValidator, 'get_metadata_file_content', return_value=meta_json)
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml_path)

        assert base_validator.ignored_errors['integration.yml'] == PRESET_ERROR_TO_IGNORE['non-certified-partner']


def test_check_support_status_certified_partner_file(repo, mocker):
    """
    Given
    - An certified partner supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the resulting ignored errors list includes the community ignore-list.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    meta_json = {
        PACK_METADATA_SUPPORT: "partner",
        PACK_METADATA_CERTIFICATION: "certified"
    }
    mocker.patch.object(BaseValidator, 'get_metadata_file_content', return_value=meta_json)
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml_path)

        assert 'integration.yml' not in base_validator.ignored_errors


def test_check_support_status_community_file(repo, mocker):
    """
    Given
    - An community supported integration yml.

    When
    - Running check_support_status method.

    Then
    - Ensure the resulting ignored errors list does not include the integration file name.
    """
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    meta_json = {
        PACK_METADATA_SUPPORT: "community",
        PACK_METADATA_CERTIFICATION: "not certified"
    }
    mocker.patch.object(BaseValidator, 'get_metadata_file_content', return_value=meta_json)
    pack.pack_metadata.write_json(meta_json)
    with ChangeCWD(repo.path):
        base_validator = BaseValidator(ignored_errors={})
        base_validator.update_checked_flags_by_support_level(integration.yml_path)

        assert base_validator.ignored_errors['integration.yml'] == PRESET_ERROR_TO_IGNORE['community']

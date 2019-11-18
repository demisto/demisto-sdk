import os
import pytest


from demisto_sdk.common.hook_validations.structure import StructureValidator
from demisto_sdk.common.constants import PLAYBOOK_REGEX


FILES_PATH = os.path.normpath(os.path.join(__file__, '..', 'test_files'))


def test_scheme_validation_playbook():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-test.yml'), use_git=False)

    assert validator.is_valid_scheme(matching_regex=PLAYBOOK_REGEX), \
        "Found a problem in the scheme although there is no problem"


def test_scheme_validation_invalid_playbook():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    try:
        validator.is_valid_scheme(matching_regex=PLAYBOOK_REGEX)
    except TypeError as exc:
        pytest.raises(TypeError, exc)


def test_version_validation():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-test.yml'), use_git=False)

    assert validator.is_valid_version(), \
        "Found an incorrect version although the version is -1"


def test_incorrect_version_validation():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    assert validator.is_valid_version() is False, \
        "Found an a correct version although the version is 123"


def test_fromversion_update_validation_yml_structure():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-test.yml'), use_git=False)

    change_string = "+ fromversion: sometext"
    assert validator.is_valid_fromversion_on_modified(change_string=change_string) is False, \
        "Didn't find the fromversion as updated in yml file"


def test_fromversion_update_validation_json_structure():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    change_string = "+ \"fromVersion\": \"123"
    assert validator.is_valid_fromversion_on_modified(change_string=change_string) is False, \
        "Didn't find the fromVersion as updated in json file"


def test_fromversion_no_update_validation():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    change_string = "some other text"
    assert validator.is_valid_fromversion_on_modified(change_string=change_string), \
        "Didn't find the fromversion as updated in yml file"


def test_updated_id_validation():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    change_string = "+  id: text"
    assert validator.is_id_not_modified(change_string=change_string) is False, \
        "Didn't find the id as updated in file"


def test_removed_id_validation():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    change_string = "-  id: text"
    assert validator.is_id_not_modified(change_string=change_string) is False, \
        "Didn't find the id as updated in file"


def test_not_touched_id_validation():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-invalid.yml'), use_git=False)

    change_string = "some other text"
    assert validator.is_id_not_modified(change_string=change_string), \
        "Found the ID as changed although it is not"


def test_valid_file_examination():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'Playbooks.playbook-test.yml'),
                                   is_added_file=True, use_git=False)

    assert validator.is_file_valid(), \
        "Found a problem in the scheme although there is no problem"


def test_invalid_file_examination():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'integration-test.yml'), use_git=False)

    assert validator.is_file_valid() is False, \
        "Didn't find a problem in the file although it is not valid"


def test_integration_file_with_valid_id():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'integration-valid-id-test.yml'), use_git=False)
    assert validator.is_file_id_without_slashes(), \
        "Found a slash in the file's ID even though it contains no slashes.."


def test_integration_file_with_invalid_id():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'integration-invalid-id-test.yml'), use_git=False)
    assert not validator.is_file_id_without_slashes(), \
        "Didn't find a slash in the ID even though it contains a slash."


def test_playbook_file_with_valid_id():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'playbook-valid-id-test.yml'), use_git=False)
    assert validator.is_file_id_without_slashes(), \
        "Didn't find a slash in the ID even though it contains a slash."


def test_playbook_file_with_invalid_id():
    validator = StructureValidator(file_path=os.path.join(FILES_PATH, 'playbook-invalid-id-test.yml'), use_git=False)
    assert not validator.is_file_id_without_slashes(), \
        "Didn't find a slash in the ID even though it contains a slash."

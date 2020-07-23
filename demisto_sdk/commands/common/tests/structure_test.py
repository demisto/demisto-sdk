import os
from os.path import isfile
from shutil import copyfile
from typing import List, Tuple

import pytest
import yaml
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.tests.constants_test import (
    DASHBOARD_TARGET, DIR_LIST, INCIDENT_FIELD_TARGET,
    INDICATORFIELD_EXACT_SCHEME, INDICATORFIELD_EXTRA_FIELDS,
    INDICATORFIELD_MISSING_AND_EXTRA_FIELDS, INDICATORFIELD_MISSING_FIELD,
    INTEGRATION_TARGET, INVALID_DASHBOARD_PATH, INVALID_INTEGRATION_ID_PATH,
    INVALID_INTEGRATION_YML_1, INVALID_INTEGRATION_YML_2,
    INVALID_INTEGRATION_YML_3, INVALID_INTEGRATION_YML_4,
    INVALID_LAYOUT_CONTAINER_PATH, INVALID_LAYOUT_PATH,
    INVALID_PLAYBOOK_ID_PATH, INVALID_PLAYBOOK_PATH, INVALID_REPUTATION_FILE,
    INVALID_WIDGET_PATH, LAYOUT_TARGET, LAYOUTS_CONTAINER_TARGET,
    PLAYBOOK_PACK_TARGET, PLAYBOOK_TARGET, VALID_DASHBOARD_PATH,
    VALID_INTEGRATION_ID_PATH, VALID_INTEGRATION_TEST_PATH,
    VALID_LAYOUT_CONTAINER_PATH, VALID_LAYOUT_PATH,
    VALID_PLAYBOOK_ARCSIGHT_ADD_DOMAIN_PATH, VALID_PLAYBOOK_ID_PATH,
    VALID_REPUTATION_FILE, VALID_TEST_PLAYBOOK_PATH, VALID_WIDGET_PATH,
    WIDGET_TARGET)


class TestStructureValidator:
    INPUTS_TARGETS = [
        LAYOUTS_CONTAINER_TARGET,
        LAYOUT_TARGET,
        DASHBOARD_TARGET,
        WIDGET_TARGET,
        PLAYBOOK_TARGET,
        INTEGRATION_TARGET,
        INCIDENT_FIELD_TARGET,
        PLAYBOOK_PACK_TARGET,
    ]
    CREATED_DIRS = list()  # type: List

    @classmethod
    def setup_class(cls):
        # checking that the files in the test are not exists so they won't overwrites.
        for target in cls.INPUTS_TARGETS:
            if isfile(target) is True:
                pytest.fail(f"{target} File in tests already exists!")
        # Creating directory for tests if they're not exists

        for directory in DIR_LIST:
            if not os.path.exists(directory):
                cls.CREATED_DIRS.append(directory)
                os.makedirs(directory)

    @classmethod
    def teardown_class(cls):
        for target in cls.INPUTS_TARGETS:
            if isfile(target) is True:
                os.remove(target)
        for directory in cls.CREATED_DIRS:
            if os.path.exists(directory):
                os.rmdir(directory)

    SCHEME_VALIDATION_INPUTS = [
        (VALID_TEST_PLAYBOOK_PATH, 'playbook', True, "Found a problem in the scheme although there is no problem"),
        (VALID_PLAYBOOK_ARCSIGHT_ADD_DOMAIN_PATH, 'playbook', True,
         "Found a problem in the scheme although there is no problem"),
        (INVALID_PLAYBOOK_PATH, 'playbook', False, "Found no problem in the scheme although there is a problem")
    ]

    @pytest.mark.parametrize("path, scheme, answer, error", SCHEME_VALIDATION_INPUTS)
    def test_scheme_validation_playbook(self, path, scheme, answer, error, mocker):
        mocker.patch.object(StructureValidator, 'scheme_of_file_by_path', return_value=scheme)
        validator = StructureValidator(file_path=path)
        assert validator.is_valid_scheme() is answer, error

    SCHEME_VALIDATION_INDICATORFIELDS = [
        (INDICATORFIELD_EXACT_SCHEME, INCIDENT_FIELD_TARGET, True),
        (INDICATORFIELD_EXTRA_FIELDS, INCIDENT_FIELD_TARGET, True),
        (INDICATORFIELD_MISSING_FIELD, INCIDENT_FIELD_TARGET, False),
        (INDICATORFIELD_MISSING_AND_EXTRA_FIELDS, INCIDENT_FIELD_TARGET, False)
    ]

    @pytest.mark.parametrize("path, scheme, answer", SCHEME_VALIDATION_INDICATORFIELDS)
    def test_scheme_validation_indicatorfield(self, path, scheme, answer, mocker):
        validator = StructureValidator(file_path=path, predefined_scheme='incidentfield')
        assert validator.is_valid_scheme() is answer

    SCHEME_VALIDATION_REPUTATION = [
        (VALID_REPUTATION_FILE, True),
        (INVALID_REPUTATION_FILE, False)
    ]

    @pytest.mark.parametrize("path, answer", SCHEME_VALIDATION_REPUTATION)
    def test_scheme_validation_reputation(self, path, answer):
        validator = StructureValidator(file_path=path, predefined_scheme='reputation')
        assert validator.is_valid_scheme() is answer

    INPUTS_VALID_FROM_VERSION_MODIFIED = [
        (VALID_TEST_PLAYBOOK_PATH, INVALID_PLAYBOOK_PATH, False),
        (INVALID_PLAYBOOK_PATH, VALID_PLAYBOOK_ID_PATH, False),
        (INVALID_PLAYBOOK_PATH, INVALID_PLAYBOOK_PATH, True)
    ]

    @pytest.mark.parametrize('path, old_file_path, answer', INPUTS_VALID_FROM_VERSION_MODIFIED)
    def test_fromversion_update_validation_yml_structure(self, path, old_file_path, answer):
        validator = StructureValidator(file_path=path)
        with open(old_file_path) as f:
            validator.old_file = yaml.safe_load(f)
            assert validator.is_valid_fromversion_on_modified() is answer

    INPUTS_IS_ID_MODIFIED = [
        (INVALID_PLAYBOOK_PATH, VALID_PLAYBOOK_ID_PATH, True, "Didn't find the id as updated in file"),
        (VALID_PLAYBOOK_ID_PATH, VALID_PLAYBOOK_ID_PATH, False, "Found the ID as changed although it is not")
    ]

    @pytest.mark.parametrize("current_file, old_file, answer, error", INPUTS_IS_ID_MODIFIED)
    def test_is_id_modified(self, current_file, old_file, answer, error):
        validator = StructureValidator(file_path=current_file)
        with open(old_file) as f:
            validator.old_file = yaml.safe_load(f)
            assert validator.is_id_modified() is answer, error

    POSITIVE_ERROR = "Didn't find a slash in the ID even though it contains a slash."
    NEGATIVE_ERROR = "found a slash in the ID even though it not contains a slash."
    INPUTS_IS_FILE_WITHOUT_SLASH = [
        (VALID_INTEGRATION_ID_PATH, True, POSITIVE_ERROR),
        (INVALID_INTEGRATION_ID_PATH, False, NEGATIVE_ERROR),
        (VALID_PLAYBOOK_ID_PATH, True, POSITIVE_ERROR),
        (INVALID_PLAYBOOK_ID_PATH, False, NEGATIVE_ERROR)

    ]

    @pytest.mark.parametrize('path, answer, error', INPUTS_IS_FILE_WITHOUT_SLASH)
    def test_integration_file_with_valid_id(self, path, answer, error):
        validator = StructureValidator(file_path=path)
        assert validator.is_file_id_without_slashes() is answer, error

    INPUTS_IS_PATH_VALID = [
        ("Packs/Test/Reports/report-sade.json", True),
        ("Notinregex/report-sade.json", False),
        ("Packs/Test/Integrations/Cymon/Cymon.yml", True),
    ]

    @pytest.mark.parametrize('path, answer', INPUTS_IS_PATH_VALID)
    def test_is_valid_file_path(self, path, answer, mocker):
        mocker.patch.object(StructureValidator, "load_data_from_file", return_value=None)
        structure = StructureValidator(path)
        structure.scheme_name = None
        assert structure.is_valid_file_path() is answer

    INPUTS_IS_VALID_FILE = [
        (VALID_LAYOUT_PATH, LAYOUT_TARGET, True),
        (INVALID_LAYOUT_PATH, LAYOUT_TARGET, False),
        (VALID_LAYOUT_CONTAINER_PATH, LAYOUTS_CONTAINER_TARGET, True),
        (INVALID_LAYOUT_CONTAINER_PATH, LAYOUTS_CONTAINER_TARGET, False),
        (INVALID_WIDGET_PATH, WIDGET_TARGET, False),
        (VALID_WIDGET_PATH, WIDGET_TARGET, True),
        (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, True),
        (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, True),
        (INVALID_PLAYBOOK_PATH, INTEGRATION_TARGET, False),
    ]  # type: List[Tuple[str, str, bool]]

    @pytest.mark.parametrize('source, target, answer', INPUTS_IS_VALID_FILE)
    def test_is_file_valid(self, source, target, answer, mocker):
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        try:
            copyfile(source, target)
            structure = StructureValidator(target)
            assert structure.is_valid_file() is answer
        finally:
            os.remove(target)

    pykwalify_error_1 = "'<SchemaError: error code 2: Schema validation failed:\n" \
                        " - Cannot find required key \'category\'. Path: \'\'.: Path: \'/\'>'"
    expected_error_1 = "Missing category in root"
    pykwalify_error_2 = "'<SchemaError: error code 2: Schema validation failed:\n" \
                        " - Cannot find required key \'id\'. Path: \'/commonfields\'.: Path: \'/\'>'"
    expected_error_2 = "Missing id in \nversion: -1\n\nPath: 'commonfields'"
    pykwalify_error_3 = "'<SchemaError: error code 2: Schema validation failed:\n" \
                        " - Cannot find required key \'description\'. Path: \'/script/commands/0/arguments/0\'.: " \
                        "Path: \'/\'>'"
    expected_error_3 = "Missing description in \ntop-priority\n...\n\nPath: 'script'-> 'commands'-> " \
                       "'integrationTest-search-vulnerabilities'-> 'arguments'-> 'top-priority'"
    pykwalify_error_4 = "'<SchemaError: error code 2: Schema validation failed:\n " \
                        "- Cannot find required key \'description\'. Path: \'/script/commands/5/outputs/0\'.: " \
                        "Path: \'/\'>'"
    expected_error_4 = "Missing description in \nintegrationTest.ConnectorsList.ID\n...\n\nPath: 'script'-> " \
                       "'commands'-> 'integrationTest-get-connectors'-> 'outputs'-> 'integrationTest.ConnectorsList.ID'"

    TEST_ERRORS = [
        (INVALID_INTEGRATION_YML_1, 'integration', pykwalify_error_1, expected_error_1),
        (INVALID_INTEGRATION_YML_2, 'integration', pykwalify_error_2, expected_error_2),
        (INVALID_INTEGRATION_YML_3, 'integration', pykwalify_error_3, expected_error_3),
        (INVALID_INTEGRATION_YML_4, 'integration', pykwalify_error_4, expected_error_4),
    ]  # type: List[Tuple[str,str,str, str]]

    @pytest.mark.parametrize('path, scheme , error, correct', TEST_ERRORS)
    def test_print_error_msg(self, path, scheme, error, correct, mocker):
        mocker.patch.object(StructureValidator, 'scheme_of_file_by_path', return_value=scheme)
        structure = StructureValidator(file_path=path)
        err = structure.parse_error_line(error)
        assert correct in err

    def test_check_for_spaces_in_file_name(self, mocker):
        mocker.patch.object(StructureValidator, "handle_error", return_value='Not-non-string')
        file_with_spaces = "Packs/pack/Classifiers/space in name"
        file_without_spaces = "Packs/pack/Classifiers/no-space-in-name"
        structure = StructureValidator(file_path=file_with_spaces)
        assert structure.check_for_spaces_in_file_name() is False

        structure = StructureValidator(file_path=file_without_spaces)
        assert structure.check_for_spaces_in_file_name() is True

    def test_is_valid_file_extension(self, mocker):
        mocker.patch.object(StructureValidator, "handle_error", return_value='Not-non-string')
        mocker.patch.object(StructureValidator, 'load_data_from_file', return_value="")
        image = "image.png"
        yml_file = "yml_file.yml"
        json_file = "json_file.json"
        md_file = "md_file.md"
        non_valid_file = "not_valid.py"
        no_extension = "no_ext"

        structure = StructureValidator(file_path=image)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=yml_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=json_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=md_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=non_valid_file)
        assert not structure.is_valid_file_extension()

        structure = StructureValidator(file_path=no_extension)
        assert not structure.is_valid_file_extension()

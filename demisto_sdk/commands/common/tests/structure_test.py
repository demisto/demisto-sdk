import logging
import os
from pathlib import Path
from shutil import copyfile
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.constants import (
    CODE_FILES_REGEX,
    CORRELATION_RULES_YML_REGEX,
    MODELING_RULE_SCHEMA_REGEX,
    MODELING_RULE_YML_REGEX,
    PACK_LAYOUT_RULE_JSON_REGEX,
    PACKAGE_YML_FILE_REGEX,
    PACKS_CLASSIFIER_JSON_5_9_9_REGEX,
    PACKS_CLASSIFIER_JSON_REGEX,
    PACKS_DASHBOARD_JSON_REGEX,
    PACKS_INCIDENT_FIELD_JSON_REGEX,
    PACKS_INCIDENT_TYPE_JSON_REGEX,
    PACKS_INTEGRATION_NON_SPLIT_YML_REGEX,
    PACKS_INTEGRATION_PY_REGEX,
    PACKS_INTEGRATION_TEST_PY_REGEX,
    PACKS_INTEGRATION_YML_REGEX,
    PACKS_LAYOUT_JSON_REGEX,
    PACKS_LAYOUTS_CONTAINER_JSON_REGEX,
    PACKS_MAPPER_JSON_REGEX,
    PACKS_SCRIPT_PY_REGEX,
    PACKS_SCRIPT_TEST_PLAYBOOK,
    PACKS_SCRIPT_TEST_PY_REGEX,
    PACKS_SCRIPT_YML_REGEX,
    PACKS_WIDGET_JSON_REGEX,
    PARSING_RULE_YML_REGEX,
    PLAYBOOK_README_REGEX,
    PLAYBOOK_YML_REGEX,
    TEST_PLAYBOOK_YML_REGEX,
    TRIGGER_JSON_REGEX,
    XDRC_TEMPLATE_JSON_REGEX,
    XDRC_TEMPLATE_YML_REGEX,
    XSIAM_DASHBOARD_JSON_REGEX,
    XSIAM_REPORT_JSON_REGEX,
    FileType,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.hook_validations.structure import (
    StructureValidator,
    checked_type_by_reg,
)
from demisto_sdk.commands.common.tools import get_file, write_dict
from demisto_sdk.tests.constants_test import (
    DASHBOARD_TARGET,
    DIR_LIST,
    INCIDENT_FIELD_TARGET,
    INDICATORFIELD_EXACT_SCHEME,
    INDICATORFIELD_EXTRA_FIELDS,
    INDICATORFIELD_MISSING_AND_EXTRA_FIELDS,
    INDICATORFIELD_MISSING_FIELD,
    INTEGRATION_TARGET,
    INVALID_DASHBOARD_PATH,
    INVALID_INTEGRATION_ID_PATH,
    INVALID_INTEGRATION_YML_1,
    INVALID_INTEGRATION_YML_2,
    INVALID_INTEGRATION_YML_3,
    INVALID_INTEGRATION_YML_4,
    INVALID_LAYOUT_CONTAINER_PATH,
    INVALID_LAYOUT_PATH,
    INVALID_PLAYBOOK_PATH,
    INVALID_REPUTATION_FILE,
    INVALID_WIDGET_PATH,
    LAYOUT_TARGET,
    LAYOUTS_CONTAINER_TARGET,
    PLAYBOOK_PACK_TARGET,
    PLAYBOOK_TARGET,
    VALID_DASHBOARD_PATH,
    VALID_INTEGRATION_ID_PATH,
    VALID_INTEGRATION_TEST_PATH,
    VALID_LAYOUT_CONTAINER_PATH,
    VALID_LAYOUT_PATH,
    VALID_PLAYBOOK_ARCSIGHT_ADD_DOMAIN_PATH,
    VALID_PLAYBOOK_ID_PATH,
    VALID_REPUTATION_FILE,
    VALID_TEST_PLAYBOOK_PATH,
    VALID_WIDGET_PATH,
    WIDGET_TARGET,
)
from TestSuite.json_based import JSONBased
from TestSuite.pack import Pack
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list


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
    CREATED_DIRS: List = list()

    @classmethod
    def setup_class(cls):
        # checking that the files in the test are not exists so they won't overwrites.
        for target in cls.INPUTS_TARGETS:
            if Path(target).is_file():
                pytest.fail(f"{target} File in tests already exists!")
        # Creating directory for tests if they're not exists

        for directory in DIR_LIST:
            if not Path(directory).exists():
                cls.CREATED_DIRS.append(directory)
                os.makedirs(directory)

    @classmethod
    def teardown_class(cls):
        for target in cls.INPUTS_TARGETS:
            Path(target).unlink(missing_ok=True)
        for directory in cls.CREATED_DIRS:
            if Path(directory).exists():
                os.rmdir(directory)

    SCHEME_VALIDATION_INPUTS = [
        (
            VALID_TEST_PLAYBOOK_PATH,
            "playbook",
            True,
            "Found a problem in the scheme although there is no problem",
        ),
        (
            VALID_PLAYBOOK_ARCSIGHT_ADD_DOMAIN_PATH,
            "playbook",
            True,
            "Found a problem in the scheme although there is no problem",
        ),
        (
            INVALID_PLAYBOOK_PATH,
            "playbook",
            False,
            "Found no problem in the scheme although there is a problem",
        ),
    ]

    @pytest.mark.parametrize("path, scheme, answer, error", SCHEME_VALIDATION_INPUTS)
    def test_scheme_validation_playbook(self, path, scheme, answer, error, mocker):
        mocker.patch.object(
            StructureValidator, "scheme_of_file_by_path", return_value=scheme
        )
        validator = StructureValidator(file_path=path)
        assert validator.is_valid_scheme() is answer, error

    SCHEME_VALIDATION_INDICATORFIELDS = [
        (INDICATORFIELD_EXACT_SCHEME, INCIDENT_FIELD_TARGET, True),
        (INDICATORFIELD_EXTRA_FIELDS, INCIDENT_FIELD_TARGET, False),
        (INDICATORFIELD_MISSING_FIELD, INCIDENT_FIELD_TARGET, False),
        (INDICATORFIELD_MISSING_AND_EXTRA_FIELDS, INCIDENT_FIELD_TARGET, False),
    ]

    @pytest.mark.parametrize("path, scheme, answer", SCHEME_VALIDATION_INDICATORFIELDS)
    def test_scheme_validation_indicatorfield(self, path, scheme, answer, mocker):
        validator = StructureValidator(
            file_path=path, predefined_scheme="incidentfield"
        )
        assert validator.is_valid_scheme() is answer

    SCHEME_VALIDATION_REPUTATION = [
        (VALID_REPUTATION_FILE, True),
        (INVALID_REPUTATION_FILE, False),
    ]

    @pytest.mark.parametrize("path, answer", SCHEME_VALIDATION_REPUTATION)
    def test_scheme_validation_reputation(self, path, answer):
        validator = StructureValidator(file_path=path, predefined_scheme="reputation")
        assert validator.is_valid_scheme() is answer

    POSITIVE_ERROR = "Didn't find a slash in the ID even though it contains a slash."
    NEGATIVE_ERROR = "found a slash in the ID even though it not contains a slash."
    INPUTS_IS_FILE_WITHOUT_SLASH = [
        (VALID_INTEGRATION_ID_PATH, True, POSITIVE_ERROR),
        (INVALID_INTEGRATION_ID_PATH, False, NEGATIVE_ERROR),
        (VALID_PLAYBOOK_ID_PATH, True, POSITIVE_ERROR),
    ]

    @pytest.mark.parametrize("path, answer, error", INPUTS_IS_FILE_WITHOUT_SLASH)
    def test_integration_file_with_valid_id(self, path, answer, error):
        validator = StructureValidator(file_path=path)
        assert validator.is_file_id_without_slashes() is answer, error

    INPUTS_IS_PATH_VALID = [
        ("Packs/Test/Reports/report-sade.json", True),
        ("Notinregex/report-sade.json", False),
        ("Packs/Test/Integrations/Cymon/Cymon.yml", True),
    ]

    @pytest.mark.parametrize("path, answer", INPUTS_IS_PATH_VALID)
    def test_is_valid_file_path(self, path, answer, mocker):
        mocker.patch.object(
            StructureValidator, "load_data_from_file", return_value=None
        )
        structure = StructureValidator(path)
        structure.scheme_name = None
        assert structure.is_valid_file_path() is answer

    INPUTS_IS_VALID_FILE: List[Tuple[str, str, bool]] = [
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
    ]

    @pytest.mark.parametrize("source, target, answer", INPUTS_IS_VALID_FILE)
    def test_is_file_valid(self, source, target, answer, mocker):
        mocker.patch.object(BaseValidator, "check_file_flags", return_value="")
        try:
            copyfile(source, target)
            structure = StructureValidator(target)
            assert structure.is_valid_file() is answer
        finally:
            Path(target).unlink()

    pykwalify_error_1 = " - Cannot find required key 'category'. Path: ''.: Path: '/'>'"
    expected_error_1 = 'Missing the field "category" in root'
    pykwalify_error_2 = (
        " - Cannot find required key 'id'. Path: '/commonfields'.: Path: '/'>'"
    )
    expected_error_2 = "Missing the field \"id\" in Path: 'commonfields'"
    pykwalify_error_3 = (
        " - Cannot find required key 'description'. Path: '/script/commands/0/arguments/0'.: "
        "Path: '/'>'"
    )
    expected_error_3 = (
        "Missing the field \"description\" in Path: 'script'-> 'commands'-> "
        "'integrationTest-search-vulnerabilities'-> 'arguments'-> 'top-priority'"
    )
    pykwalify_error_4 = (
        " - Cannot find required key 'description'. Path: '/script/commands/5/outputs/0'.: "
        "Path: '/'>'"
    )
    expected_error_4 = (
        'Missing the field "description" in Path: '
        "'script'-> 'commands'-> 'integrationTest-get-connectors'-> "
        "'outputs'-> 'integrationTest.ConnectorsList.ID'"
    )
    pykwalify_error_5 = " - Key 'ok' was not defined. Path: '/configuration/0'"
    expected_error_5 = (
        "The field \"ok\" in path 'configuration'-> 'url' was not defined in the scheme"
    )
    pykwalify_error_6 = (
        "- Enum 'Network Securitys' does not exist. "
        "Path: '/category' Enum: ['Analytics & SIEM', 'Utilities', 'Messaging']."
    )
    expected_error_6 = (
        "The value \"Network Securitys\" in 'category' is invalid "
        "- legal values include: 'Analytics & SIEM', 'Utilities', 'Messaging'"
    )

    TEST_ERRORS: List[Tuple[str, str, str, str]] = [
        (INVALID_INTEGRATION_YML_1, "integration", pykwalify_error_1, expected_error_1),
        (INVALID_INTEGRATION_YML_2, "integration", pykwalify_error_2, expected_error_2),
        (INVALID_INTEGRATION_YML_3, "integration", pykwalify_error_3, expected_error_3),
        (INVALID_INTEGRATION_YML_4, "integration", pykwalify_error_4, expected_error_4),
        (INVALID_INTEGRATION_YML_4, "integration", pykwalify_error_5, expected_error_5),
        (INVALID_INTEGRATION_YML_4, "integration", pykwalify_error_6, expected_error_6),
    ]

    @pytest.mark.parametrize("path, scheme , error, correct", TEST_ERRORS)
    def test_print_error_line(self, path, scheme, error, correct, mocker):
        mocker.patch.object(
            StructureValidator, "scheme_of_file_by_path", return_value=scheme
        )
        structure = StructureValidator(file_path=path)
        err = structure.parse_error_line(error)
        assert correct in err[0]

    def test_check_for_spaces_in_file_name(self, mocker):
        mocker.patch.object(
            StructureValidator, "handle_error", return_value="Not-non-string"
        )
        file_with_spaces = "Packs/pack/Classifiers/space in name"
        file_without_spaces = "Packs/pack/Classifiers/no-space-in-name"
        structure = StructureValidator(file_path=file_with_spaces)
        assert structure.check_for_spaces_in_file_name() is False

        structure = StructureValidator(file_path=file_without_spaces)
        assert structure.check_for_spaces_in_file_name() is True

    def test_is_valid_file_extension(self, mocker):
        mocker.patch.object(
            StructureValidator, "handle_error", return_value="Not-non-string"
        )
        mocker.patch.object(StructureValidator, "load_data_from_file", return_value="")
        image = "image.png"
        yml_file = "yml_file.yml"
        json_file = "json_file.json"
        md_file = "md_file.md"
        python_file = "py_file.py"
        no_extension = "no_ext"

        structure = StructureValidator(file_path=image)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=yml_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=json_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=md_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=python_file)
        assert structure.is_valid_file_extension()

        structure = StructureValidator(file_path=no_extension)
        assert not structure.is_valid_file_extension()

    def test_is_field_with_open_ended(self, pack: Pack):
        field_content = {
            "cliName": "sanityname",
            "name": "sanity name",
            "id": "incident",
            "content": True,
            "type": "multiSelect",
            "openEnded": True,
        }
        incident_field: JSONBased = pack.create_incident_field(
            "incident-field-test", content=field_content
        )
        structure = StructureValidator(incident_field.path)
        assert structure.is_valid_scheme()

    def test_is_indicator_with_open_ended(self, pack: Pack):
        field_content = {
            "cliName": "sanityname",
            "name": "sanity name",
            "id": "incident",
            "content": True,
            "type": "multiSelect",
            "openEnded": True,
        }
        incident_field: JSONBased = pack.create_indicator_field(
            "incident-field-test", content=field_content
        )
        structure = StructureValidator(incident_field.path)
        assert structure.is_valid_scheme()

    @pytest.mark.parametrize("is_feed", (True, False))
    @pytest.mark.parametrize(
        "missing_field",
        (
            "isFeed",
            "selectedFeeds",
            "isAllFeeds",
            "name",
            "id",
            "fromVersion",
            "playbookId",
        ),
    )
    def test_job_missing_field(
        self, repo, mocker, monkeypatch, is_feed: bool, missing_field: str
    ):
        """
        Given
                A Job object in a repo, with one of the required fields missing
        When
                Validating the file
        Then
                Ensure the structure validator raises a suitable error
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        pack = repo.create_pack()
        job = pack.create_job(is_feed=is_feed, name="job_name")
        job.remove(missing_field)

        validator = StructureValidator(job.path, is_new_file=True)
        with ChangeCWD(repo.path):
            assert not validator.is_valid_file()
        assert str_in_call_args_list(
            logger_error.call_args_list,
            f'Missing the field "{missing_field}" in root',
        )

    @pytest.mark.parametrize(
        "missing_field", ("dependency_packs", "wizard", "name", "id", "fromVersion")
    )
    def test_wizard_missing_field(self, repo, mocker, monkeypatch, missing_field: str):
        """
        Given
                A Job object in a repo, with one of the required fields missing
        When
                Validating the file
        Then
                Ensure the structure validator raises a suitable error
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        pack = repo.create_pack()
        wizard = pack.create_wizard(name="wizard_name")
        wizard.remove(missing_field)

        validator = StructureValidator(wizard.path, is_new_file=True)
        with ChangeCWD(repo.path):
            assert not validator.is_valid_file()
        assert str_in_call_args_list(
            logger_error.call_args_list,
            f'Missing the field "{missing_field}" in root',
        )

    def test_validate_field_with_pretty_name(self, pack: Pack):
        """
        Given
            Incident field with a prettyName field.
        When
            Validating the item.
        Then
            Ensures the schema is valid.
        """
        field_content = {
            "cliName": "mainfield",
            "name": "main field",
            "id": "incident",
            "prettyName": "Host",
            "content": True,
            "type": "longText",
            "Aliases": [
                {
                    "cliName": "aliasfield",
                    "type": "shortText",
                    "name": "Alias Field",
                }
            ],
        }
        incident_field: JSONBased = pack.create_incident_field(
            "incident-field-test",
            content=field_content,
        )
        structure = StructureValidator(incident_field.path)
        assert structure.is_valid_scheme()

    def test_validate_field_with_alias_to(self, pack: Pack):
        """
        Given
            Incident field with an aliasTo field.
        When
            Validating the item.
        Then
            Ensures the schema is valid.
        """
        field_content = {
            "cliName": "mainfield",
            "name": "main field",
            "id": "incident",
            "prettyName": "Host",
            "content": True,
            "type": "longText",
            "aliasTo": "someotherfield",
        }
        incident_field: JSONBased = pack.create_incident_field(
            "incident-field-test",
            content=field_content,
        )
        structure = StructureValidator(incident_field.path)
        assert structure.is_valid_scheme()

    def test_validate_field_with_aliases__valid(self, pack: Pack):
        """
        Given
            Incident field with a valid Aliases field.
        When
            Validating the item.
        Then
            Ensures the schema is valid.
        """
        field_content = {
            "cliName": "mainfield",
            "name": "main field",
            "id": "incident",
            "content": True,
            "type": "longText",
            "Aliases": [
                {
                    "cliName": "aliasfield",
                    "type": "shortText",
                    "name": "Alias Field",
                }
            ],
        }
        incident_field: JSONBased = pack.create_incident_field(
            "incident-field-test",
            content=field_content,
        )
        structure = StructureValidator(incident_field.path)
        assert structure.is_valid_scheme()

    def test_validate_field_with_aliases__invalid_type(self, pack: Pack):
        """
        Given
            - Incident field with a Aliases field that has an entry with an invalid type.
        When
            - Validating the item.
        Then
            - Ensures the schema is invalid.
        """
        field_content = {
            "cliName": "mainfield",
            "name": "main field",
            "id": "incident",
            "content": True,
            "type": "longText",
            "Aliases": [{"cliName": "alias field", "type": "UNKNOWN"}],
        }
        incident_field: JSONBased = pack.create_incident_field(
            "incident-field-test", content=field_content
        )
        structure = StructureValidator(incident_field.path)
        assert not structure.is_valid_scheme()

    def test_with_marketplace_suffix(self, mocker, tmp_path):
        mocker.patch.object(
            StructureValidator, "get_file_type", return_value=FileType.INTEGRATION
        )
        mocker.patch.object(
            StructureValidator,
            "scheme_of_file_by_path",
            return_value=FileType.INTEGRATION,
        )
        yml = get_file(VALID_INTEGRATION_TEST_PATH)
        yml["name:xsoar"] = "xsoar"
        yml["name:marketplacev2"] = "xsiam"
        yml["name:xpanse"] = "xspanse"
        yml["configuration"][0]["defaultvalue:xsoar_saas"] = "xsoar_saas"
        write_dict(tmp_path / "integration.yml", yml)

        structure = StructureValidator(str(tmp_path / "integration.yml"))
        assert structure.is_valid_scheme()

        yml["commonfields"]["id:xsoar"] = "not-valid"  # can't edit the id

        write_dict(tmp_path / "integration-invalid.yml", yml)

        structure = StructureValidator(str(tmp_path / "integration-invalid.yml"))
        assert not structure.is_valid_scheme()


class TestGetMatchingRegex:
    INPUTS = [
        (
            "Packs/XDR/Playbooks/XDR.yml",
            [PLAYBOOK_YML_REGEX, TEST_PLAYBOOK_YML_REGEX],
            PLAYBOOK_YML_REGEX,
        ),
        (
            "Packs/XDR/NoMatch/XDR.yml",
            [PLAYBOOK_YML_REGEX, TEST_PLAYBOOK_YML_REGEX],
            False,
        ),
    ]

    @pytest.mark.parametrize("string_to_match, regexes, answer", INPUTS)
    def test_get_matching_regex(self, string_to_match, regexes, answer):
        assert checked_type_by_reg(string_to_match, regexes, True) == answer

    test_packs_regex_params = [
        (
            [
                "Packs/XDR/Integrations/XDR/XDR.yml",
                "Packs/XDR/Scripts/Random/Random.yml",
            ],
            ["Packs/Integrations/XDR/XDR_test.py", "Packs/Scripts/Random/Random.py"],
            [PACKAGE_YML_FILE_REGEX],
        ),
        (
            ["Packs/XDR/Integrations/XDR/XDR.py"],
            [
                "Packs/Integrations/XDR/XDR_test.py",
                "Packs/Sade/Integrations/XDR/test_yarden.py",
            ],
            [PACKS_INTEGRATION_PY_REGEX],
        ),
        (
            ["Packs/XDR/Integrations/XDR/XDR.yml"],
            ["Packs/Integrations/XDR/XDR_test.py"],
            [PACKS_INTEGRATION_YML_REGEX],
        ),
        (
            ["Packs/Sade/Integrations/XDR/XDR_test.py"],
            ["Packs/Sade/Integrations/yarden.py"],
            [PACKS_INTEGRATION_TEST_PY_REGEX],
        ),
        (
            ["Packs/XDR/Scripts/Random/Random.yml"],
            ["Packs/Scripts/Random/Random.py"],
            [PACKS_SCRIPT_YML_REGEX],
        ),
        (
            ["Packs/XDR/Scripts/Random/Random.py"],
            ["Packs/Scripts/Random/Random_test.py"],
            [PACKS_SCRIPT_PY_REGEX],
        ),
        (
            ["Packs/XDR/Scripts/Random/Random_test.py"],
            ["Packs/Sade/Scripts/test_yarden.pt"],
            [PACKS_SCRIPT_TEST_PY_REGEX],
        ),
        (
            ["Packs/XDR/Playbooks/XDR.yml"],
            ["Packs/Playbooks/XDR/XDR_test.py"],
            [PLAYBOOK_YML_REGEX],
        ),
        (
            ["Packs/XDR/TestPlaybooks/playbook.yml"],
            ["Packs/TestPlaybooks/nonpb.xml"],
            [TEST_PLAYBOOK_YML_REGEX],
        ),
        (
            ["Packs/Sade/Classifiers/classifier-yarden.json"],
            ["Packs/Sade/Classifiers/classifier-yarden-json.txt"],
            [PACKS_CLASSIFIER_JSON_REGEX],
        ),
        (
            ["Packs/Sade/Classifiers/classifier-test_5_9_9.json"],
            ["Packs/Sade/Classifiers/classifier-test_5_9_9-json.txt"],
            [PACKS_CLASSIFIER_JSON_5_9_9_REGEX],
        ),
        (
            ["Packs/Sade/Classifiers/classifier-mapper-test.json"],
            ["Packs/Sade/Classifiers/classifier-mapper-test.txt"],
            [PACKS_MAPPER_JSON_REGEX],
        ),
        (
            ["Packs/Sade/Dashboards/yarden.json"],
            ["Packs/Sade/Dashboards/yarden-json.txt"],
            [PACKS_DASHBOARD_JSON_REGEX],
        ),
        (
            ["Packs/Sade/IncidentTypes/yarden.json"],
            ["Packs/Sade/IncidentTypes/yarden-json.txt"],
            [PACKS_INCIDENT_TYPE_JSON_REGEX],
        ),
        (
            ["Packs/Sade/Widgets/yarden.json"],
            ["Packs/Sade/Widgets/yarden-json.txt"],
            [PACKS_WIDGET_JSON_REGEX],
        ),
        (
            ["Packs/Sade/Layouts/yarden.json"],
            ["Packs/Sade/Layouts/yarden_json.yml"],
            [PACKS_LAYOUT_JSON_REGEX],
        ),
        (
            ["Packs/Sade/Layouts/layoutscontainer-test.json"],
            ["Packs/Sade/Layouts/yarden_json.yml"],
            [PACKS_LAYOUTS_CONTAINER_JSON_REGEX],
        ),
        (
            ["Packs/Sade/IncidentFields/yarden.json"],
            ["Packs/Sade/IncidentFields/yarden-json.txt"],
            [PACKS_INCIDENT_FIELD_JSON_REGEX],
        ),
        (
            ["Packs/XDR/Playbooks/playbook-Test.yml", "Packs/XDR/Playbooks/Test.yml"],
            ["Packs/XDR/Playbooks/playbook-Test_CHANGELOG.md"],
            [PLAYBOOK_YML_REGEX],
        ),
        (
            ["Packs/OpenPhish/Integrations/integration-OpenPhish.yml"],
            ["Packs/OpenPhish/Integrations/OpenPhish/OpenPhish.yml"],
            [PACKS_INTEGRATION_NON_SPLIT_YML_REGEX],
        ),
        (
            ["Packs/OpenPhish/Playbooks/playbook-Foo_README.md"],
            ["Packs/OpenPhish/Playbooks/playbook-Foo_README.yml"],
            [PLAYBOOK_README_REGEX],
        ),
        (
            ["Packs/DeveloperTools/TestPlaybooks/script-CallTableToMarkdown.yml"],
            ["Packs/DeveloperTools/TestPlaybooks/CallTableToMarkdown.yml"],
            [PACKS_SCRIPT_TEST_PLAYBOOK],
        ),
        (
            ["Packs/DeveloperTools/TestPlaybooks/CallTableToMarkdown.yml"],
            ["Packs/DeveloperTools/TestPlaybooks/script-CallTableToMarkdown.yml"],
            [TEST_PLAYBOOK_YML_REGEX],
        ),
        (
            ["Packs/CyberArkIdentity/XSIAMDashboards/CyberArkDashboard.json"],
            [],
            [XSIAM_DASHBOARD_JSON_REGEX],
        ),
        (
            ["Packs/DeveloperTools/XSIAMReports/MockReport.json"],
            [],
            [XSIAM_REPORT_JSON_REGEX],
        ),
        (
            ["Packs/Core/Triggers/Trigger_-_NGFW_Scan.json"],
            [],
            [TRIGGER_JSON_REGEX],
        ),
        (
            ["Packs/Tableau/XDRCTemplates/Tableau/Tableau.json"],
            [],
            [XDRC_TEMPLATE_JSON_REGEX],
        ),
        (
            ["Packs/Tableau/XDRCTemplates/Tableau/Tableau.yml"],
            [],
            [XDRC_TEMPLATE_YML_REGEX],
        ),
        (
            ["Packs/AlibabaActionTrail/CorrelationRules/Alibaba_Correlation.yml"],
            [],
            [CORRELATION_RULES_YML_REGEX],
        ),
        (
            ["Packs/Jira/ParsingRules/JiraParsingRules/JiraParsingRules.yml"],
            [],
            [PARSING_RULE_YML_REGEX],
        ),
        (
            [
                "Packs/Okta/ModelingRules/OktaModelingRules/OktaModelingRules_schema.json"
            ],
            [],
            [MODELING_RULE_SCHEMA_REGEX],
        ),
        (
            ["Packs/Okta/ModelingRules/OktaModelingRules/OktaModelingRules.yml"],
            [],
            [MODELING_RULE_YML_REGEX],
        ),
        (
            [
                "Packs/SomeScript/Scripts/ScriptName/ScriptName.ps1",
                "Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName.ps1",
                "Packs/SomeScript/Scripts/ScriptName/ScriptName.py",
                "Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName.py",
            ],
            [
                "Packs/SomeScript/Scripts/ScriptName/ScriptName.Tests.ps1",
                "Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName.Tests.ps1",
                "Packs/SomeScript/Scripts/ScriptName/ScriptName.yml",
                "Packs/SomeScript/Scripts/ScriptName/NotTheSameScriptName.ps1",
                "Packs/SomeIntegration/Integrations/IntegrationName/NotTheSameIntegrationName.ps1",
                "Packs/SomeScript/Scripts/ScriptName/ScriptName_test.py",
                "Packs/SomeIntegration/Integrations/IntegrationName/IntegrationName_test.py",
                "Packs/SomeScript/Scripts/ScriptName/NotTheSameScriptName.py",
                "Packs/SomeIntegration/Integrations/IntegrationName/NotTheSameIntegrationName.py",
            ],
            CODE_FILES_REGEX,
        ),
        (
            ["Packs/PackName/LayoutRules/test_layout_rule.json"],
            ["Packs/PackName/test_layout_rule.json"],
            [PACK_LAYOUT_RULE_JSON_REGEX],
        ),
    ]

    @pytest.mark.parametrize("acceptable,non_acceptable,regex", test_packs_regex_params)
    def test_packs_regex(self, acceptable, non_acceptable, regex):
        for test_path in acceptable:
            assert checked_type_by_reg(test_path, compared_regexes=regex)

        for test_path in non_acceptable:
            assert not checked_type_by_reg(test_path, compared_regexes=regex)

    RELEASE_NOTES_CONFIG_SCHEME_INPUTS = [
        (dict(), True),
        ({"breakingChanges": True}, True),
        ({"breakingChanges": False}, True),
        ({"breakingChanges": True, "breakingChangesNotes": "BC"}, True),
        ({"breakingChanges": False, "breakingChangesNotes": "BC"}, True),
        ({"breakingChanges": "true", "breakingChangesNotes": "BC"}, False),
        ({"breakingChanges": True, "breakingChangesNotes": True}, False),
    ]

    @pytest.mark.parametrize(
        "release_notes_config, expected", RELEASE_NOTES_CONFIG_SCHEME_INPUTS
    )
    def test_release_notes_config_scheme(
        self, tmpdir, release_notes_config: dict, expected: bool
    ):
        file_path: str = f"{tmpdir}/1_0_1.json"
        with open(file_path, "w") as f:
            f.write(json.dumps(release_notes_config))
        validator = StructureValidator(
            file_path=file_path, predefined_scheme="releasenotesconfig"
        )
        assert validator.is_valid_scheme() is expected


class TestXSIAMStructureValidator(TestStructureValidator):
    def test_valid_modeling_rule_yml(self, pack: Pack):
        """Given a valid modeling rule yml, make sure its schema is valid."""
        modeling_rule_yml = pack.create_modeling_rule("modeling_rule").yml
        validator = StructureValidator(modeling_rule_yml.path)
        assert validator.is_valid_scheme()

    def test_invalid_modeling_rule_yml_missing_fromversion(self, pack: Pack):
        """
        Given:
            An invalid modeling rule yml with a missing fromversion field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        modeling_rule_yml = pack.create_modeling_rule("modeling_rule").yml
        modeling_rule_yml.delete_key("fromversion")
        validator = StructureValidator(modeling_rule_yml.path)
        assert not validator.is_valid_scheme()

    def test_valid_modeling_rule_schema(self, pack: Pack):
        """Given a valid modeling rule schema, make sure its schema is valid."""
        modeling_rule_schema = pack.create_modeling_rule("modeling_rule").schema
        validator = StructureValidator(modeling_rule_schema.path)
        assert validator.is_valid_scheme()

    def test_invalid_modeling_rule_schema_bad_type(self, pack: Pack):
        """
        Given:
            An invalid modeling rule schema with a bad type for the "name" field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        modeling_rule_schema = pack.create_modeling_rule("modeling_rule").schema
        modeling_rule_schema.add_or_update_field_by_path(
            "test_audit_raw.name.type", "invalid_type"
        )
        validator = StructureValidator(modeling_rule_schema.path)
        assert not validator.is_valid_scheme()

    def test_valid_parsing_rule_yml(self, pack: Pack):
        """Given a valid parsing rule, make sure its schema is valid."""
        parsing_rule_yml = pack.create_parsing_rule("parsing_rule").yml
        validator = StructureValidator(parsing_rule_yml.path)
        assert validator.is_valid_scheme()

    def test_invalid_parsing_rule_yml_missing_fromversion(self, pack: Pack):
        """
        Given:
            An invalid parsing rule with a missing fromversion field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        parsing_rule_yml = pack.create_parsing_rule("parsing_rule").yml
        parsing_rule_yml.delete_key("fromversion")
        validator = StructureValidator(parsing_rule_yml.path)
        assert not validator.is_valid_scheme()

    def test_valid_xdrc_template(self, pack: Pack):
        """Given a valid XDRC template, make sure its schema is valid."""
        xdrc_template = pack.create_xdrc_template("xdrc_template")
        validator = StructureValidator(str(xdrc_template.xdrc_template_tmp_path))
        assert validator.is_valid_scheme()

    def test_invalid_xdrc_template_missing_ostype(self, pack: Pack):
        """
        Given:
            An invalid XDRC template with a missing ostype field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        xdrc_template = pack.create_xdrc_template("xdrc_template")
        xdrc_template.remove("os_type")
        validator = StructureValidator(str(xdrc_template.xdrc_template_tmp_path))
        assert not validator.is_valid_scheme()

    def test_valid_trigger(self, pack: Pack):
        """Given a valid trigger, make sure its schema is valid."""
        trigger = pack.create_trigger("trigger")
        validator = StructureValidator(trigger.path)
        assert validator.is_valid_scheme()

    def test_invalid_trigger_missing_search_field(self, pack: Pack):
        """
        Given:
            An invalid trigger with a missing SEARCH_FIELD field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        trigger = pack.create_trigger("trigger")
        trigger.remove_field_by_path("alerts_filter.filter.AND.[0].SEARCH_FIELD")
        validator = StructureValidator(trigger.path)
        assert not validator.is_valid_scheme()

    def test_valid_layout_rule(self, pack: Pack):
        """Given a valid trigger, make sure its schema is valid."""
        layout_rule = pack.create_layout_rule("layout_rule")
        validator = StructureValidator(layout_rule.path)
        assert validator.is_valid_scheme()

    def test_invalid_layout_rule_missing_layout_id_field(self, pack: Pack):
        """
        Given:
            An invalid layout rule with a missing layout_id field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        layout_rule = pack.create_layout_rule("layout_rule")
        layout_rule.remove("layout_id")
        validator = StructureValidator(layout_rule.path)
        assert not validator.is_valid_scheme()

    def test_valid_xsiam_dashboard(self, pack: Pack):
        """Given a valid XSIAM dashboard, make sure its schema is valid."""
        xsiam_dashboard = pack.create_xsiam_dashboard("xsiam_dashboard")
        validator = StructureValidator(xsiam_dashboard.path)
        assert validator.is_valid_scheme()

    def test_invalid_xsiam_dashboard_has_creator_mail(self, pack: Pack):
        """
        Given:
            An invalid XSIAM dashboard with a creator_mail field (should not have one)
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        xsiam_dashboard = pack.create_xsiam_dashboard("xsiam_dashboard")
        xsiam_dashboard.add_or_update_field_by_path(
            "widgets_data.[0].creator_mail", "test@paloaltonetworks.com"
        )
        validator = StructureValidator(xsiam_dashboard.path)
        assert not validator.is_valid_scheme()

    def test_valid_xsiam_report(self, pack: Pack):
        """Given a valid XSIAM report, make sure its schema is valid."""
        xsiam_report = pack.create_xsiam_report("xsiam_report")
        validator = StructureValidator(xsiam_report.path)
        assert validator.is_valid_scheme()

    def test_invalid_xsiam_report_missing_global_id(self, pack: Pack):
        """
        Given:
            An invalid XSIAM report with a missing global_id field
        When:
            Running schema validation.
        Then:
            Make sure the schema is invalid.
        """
        xsiam_report = pack.create_xsiam_report("xsiam_report")
        xsiam_report.remove_field_by_path("templates_data.[0].global_id")
        validator = StructureValidator(xsiam_report.path)
        assert not validator.is_valid_scheme()

    DEPRECATED_WITH_COMMENT = {
        "comment": "Deprecated. No available replacement.",
        "deprecated": True,
    }

    DEPRECATED_RULE = {
        "deprecated": True,
    }

    @pytest.mark.parametrize(
        "yml_data_update",
        [DEPRECATED_RULE, DEPRECATED_WITH_COMMENT],
    )
    def test_deprecated_parsing_rule_is_valid(self, repo, yml_data_update):
        """
        Given:
            Case a:
                - A deprecated parsing rule without a comment.
            Case b:
                - A deprecated parsing rule with a comment.
        When:
            - Running is_schema_types_valid.
        Then:
            - Validate that the parsing rule is invalid.
        """
        with ChangeCWD(repo.path):
            pack = repo.create_pack("TestPack")
            parsing_rule = pack.create_parsing_rule(name="MyParsingRule")
            parsing_rule.yml.update(yml_data_update)
            structure_validator = StructureValidator(parsing_rule.yml.path)
        assert structure_validator.is_valid_file()

    @pytest.mark.parametrize(
        "yml_data_update",
        [DEPRECATED_RULE, DEPRECATED_WITH_COMMENT],
    )
    def test_deprecated_modeling_rule_is_valid(self, repo, yml_data_update):
        """
        Given:
            Case a:
                - A deprecated modeling rule without a comment.
            Case b:
                - A deprecated modeling rule with a comment.
        When:
            - Running is_schema_types_valid.
        Then:
            - Validate that the modeling rule is invalid.
        """
        with ChangeCWD(repo.path):
            pack = repo.create_pack("TestPack")
            modeling_rule = pack.create_modeling_rule("MyModelingRule")
            modeling_rule.yml.update(yml_data_update)
            structure_validator = StructureValidator(modeling_rule.yml.path)
            assert structure_validator.is_valid_file()

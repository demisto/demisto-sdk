import logging
from typing import Dict, List
from unittest.mock import patch

import pytest
from packaging.version import Version

from demisto_sdk.commands.common.hook_validations.field_base_validator import (
    FieldBaseValidator,
    GroupFieldTypes,
)
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from TestSuite.test_tools import str_in_call_args_list

INDICATOR_GROUP_NUMBER = 2
INCIDENT_GROUP_NUMBER = 0


class TestFieldValidator:
    NAME_SANITY_FILE = {
        "cliName": "sanityname",
        "name": "sanity name",
        "id": "incident",
        "content": True,
    }

    GOOD_NAME_1 = {
        "cliName": "sanityname",
        "name": "Alerting feature",
        "content": True,
    }

    BAD_NAME_1 = {
        "cliName": "sanityname",
        "name": "Incident",
        "content": True,
    }

    BAD_NAME_2 = {
        "cliName": "sanityname",
        "name": "case",
        "content": True,
    }

    BAD_NAME_3 = {
        "cliName": "sanityname",
        "name": "Playbook",
        "content": True,
    }

    BAD_NAME_4 = {
        "cliName": "sanity name",
        "name": "INciDeNts",
        "content": True,
    }

    INPUTS_NAMES = [
        (NAME_SANITY_FILE, False),
        (GOOD_NAME_1, False),
        (BAD_NAME_1, True),
        (BAD_NAME_2, True),
        (BAD_NAME_3, True),
        (BAD_NAME_4, True),
    ]

    @pytest.mark.parametrize("current_file, answer", INPUTS_NAMES)
    def test_is_valid_name_sanity(self, current_file, answer, mocker):
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")

        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file

            validator.is_valid_name()

            assert str_in_call_args_list(logger_error.call_args_list, "IF100") is answer

    CONTENT_1 = {"content": True}

    CONTENT_BAD_1 = {"content": False}

    CONTENT_BAD_2 = {"something": True}

    INPUTS_FLAGS = [(CONTENT_1, True), (CONTENT_BAD_1, False), (CONTENT_BAD_2, False)]

    @pytest.mark.parametrize("current_file, answer", INPUTS_FLAGS)
    def test_is_valid_content_flag_sanity(self, current_file, answer):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_valid_content_flag() is answer

    SYSTEM_FLAG_1 = {
        "system": False,
        "content": True,
    }

    SYSTEM_FLAG_BAD_1 = {
        "system": True,
        "content": True,
    }

    INPUTS_SYSTEM_FLAGS = [(SYSTEM_FLAG_1, True), (SYSTEM_FLAG_BAD_1, False)]

    @pytest.mark.parametrize("current_file, answer", INPUTS_SYSTEM_FLAGS)
    def test_is_valid_system_flag_sanity(self, current_file, answer):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_valid_system_flag() is answer

    VALID_CLINAMES_AND_GROUPS = [
        ("validind", GroupFieldTypes.INCIDENT_FIELD),
        ("validind", GroupFieldTypes.EVIDENCE_FIELD),
        ("validind", GroupFieldTypes.INDICATOR_FIELD),
    ]

    @pytest.mark.parametrize("cliname, group", VALID_CLINAMES_AND_GROUPS)
    def test_is_cliname_is_builtin_key(self, cliname, group):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            current_file = {"cliName": cliname, "group": group}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_cli_name_is_builtin_key()

    INVALID_CLINAMES_AND_GROUPS = [
        ("id", GroupFieldTypes.INCIDENT_FIELD),
        ("id", GroupFieldTypes.EVIDENCE_FIELD),
        ("id", GroupFieldTypes.INDICATOR_FIELD),
    ]

    @pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
    def test_is_cli_name_is_builtin_key_invalid(self, cliname, group):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            current_file = {"cliName": cliname, "group": group}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), {"id"})
            validator.current_file = current_file
            assert not validator.is_cli_name_is_builtin_key()

    VALID_CLINAMES = [
        ("incident_testfortest", "testfortest"),
        ("incident_test_for_test", "testfortest"),
        ("indicator_test_for_test", "testfortest"),
        ("indicator_incident_test_for_test", "incidenttestfortest"),
        ("indicator_indicator_test_for_test", "indicatortestfortest"),
    ]

    @pytest.mark.parametrize("_id, cliname", VALID_CLINAMES)
    def test_does_cli_name_match_id(self, _id, cliname):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            current_file = {"id": _id, "cliName": cliname}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.does_cli_name_match_id()

    INVALID_CLINAMES = [
        ("incident_testforfortest", "testfortest"),
        ("incident_test_for_for_test", "testfortest"),
        ("indicator_test_for_for_test", "testfortest"),
    ]

    @pytest.mark.parametrize("_id, cliname", INVALID_CLINAMES)
    def test_does_cli_name_match_id_invalid(self, _id, cliname):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            current_file = {"id": _id, "cliName": cliname}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert not validator.does_cli_name_match_id()

    VALID_CLINAMES = [
        "agoodid",
        "anot3erg00did",
    ]

    @pytest.mark.parametrize("cliname", VALID_CLINAMES)
    def test_matching_cliname_regex(self, cliname):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            current_file = {"cliName": cliname}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_matching_cli_name_regex()

    INVALID_CLINAMES = [
        "invalid cli",
        "invalid_cli",
        "invalid$$cli",
        "לאסליטוב",
    ]

    @pytest.mark.parametrize("cliname", INVALID_CLINAMES)
    def test_matching_cliname_regex_invalid(self, cliname):
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            current_file = {"cliName": cliname}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert not validator.is_matching_cli_name_regex()

    VALID_CLINAMES_AND_GROUPS = [
        ("incident_validind", "validind", GroupFieldTypes.INCIDENT_FIELD),
        ("validind", "validind", GroupFieldTypes.EVIDENCE_FIELD),
        ("indicator_validind", "validind", GroupFieldTypes.INDICATOR_FIELD),
    ]

    @pytest.mark.parametrize("_id, cliname, group", VALID_CLINAMES_AND_GROUPS)
    def test_is_valid_cliname(self, _id, cliname, group):
        current_file = {"id": _id, "cliName": cliname, "group": group}
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_valid_cli_name()

    @pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
    def test_is_valid_cli_name_invalid(self, cliname, group):
        current_file = {"cliName": cliname, "group": group}
        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), {"id"})
            validator.current_file = current_file
            assert not validator.is_valid_cli_name()

    data_is_valid_version = [
        (-1, True),
        (0, False),
        (1, False),
    ]

    @pytest.mark.parametrize("version, is_valid", data_is_valid_version)
    def test_is_valid_version(self, version, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"version": version}
        validator = FieldBaseValidator(structure, set(), set())
        assert (
            validator.is_valid_version() == is_valid
        ), f"is_valid_version({version}) returns {not is_valid}."

    IS_FROM_VERSION_CHANGED_NO_OLD: Dict[any, any] = {}
    IS_FROM_VERSION_CHANGED_OLD = {"fromVersion": "5.0.0"}
    IS_FROM_VERSION_CHANGED_NEW = {"fromVersion": "5.0.0"}
    IS_FROM_VERSION_CHANGED_NO_NEW: Dict[any, any] = {}
    IS_FROM_VERSION_CHANGED_NEW_HIGHER = {"fromVersion": "5.5.0"}
    IS_CHANGED_FROM_VERSION_INPUTS = [
        (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_OLD, False),
        (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NEW, True),
        (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW, False),
        (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_NEW, False),
        (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW_HIGHER, True),
    ]

    @pytest.mark.parametrize(
        "current_from_version, old_from_version, answer", IS_CHANGED_FROM_VERSION_INPUTS
    )
    def test_is_changed_from_version(
        self, current_from_version, old_from_version, answer
    ):
        structure = StructureValidator("")
        structure.old_file = old_from_version
        structure.current_file = current_from_version
        validator = FieldBaseValidator(structure, set(), set())
        assert validator.is_changed_from_version() is answer
        structure.quiet_bc = True
        assert validator.is_changed_from_version() is False

    data_required = [
        (True, False),
        (False, True),
    ]

    @pytest.mark.parametrize("required, is_valid", data_required)
    def test_is_valid_required(self, required, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"required": required}
        validator = FieldBaseValidator(structure, set(), set())
        assert validator.is_valid_required() == is_valid, (
            f"is_valid_required({required})" f" returns {not is_valid}."
        )

    data_is_changed_type = [
        ("shortText", "shortText", False),
        ("shortText", "longText", True),
        ("number", "number", False),
        ("shortText", "number", True),
        ("timer", "timer", False),
        ("timer", "number", True),
        ("timer", "shortText", True),
        ("singleSelect", "singleSelect", False),
        ("singleSelect", "shortText", True),
    ]

    @pytest.mark.parametrize("current_type, old_type, is_valid", data_is_changed_type)
    def test_is_changed_type(self, current_type, old_type, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"type": current_type}
        structure.old_file = {"type": old_type}
        validator = FieldBaseValidator(structure, set(), set())
        assert validator.is_changed_type() == is_valid, (
            f"is_changed_type({current_type}, {old_type})" f" returns {not is_valid}."
        )
        structure.quiet_bc = True
        assert validator.is_changed_type() is False

    FIELD_NAME1 = {
        "name": "pack name field",
    }
    FIELD_NAME2 = {
        "name": "pack prefix field",
    }
    FIELD_NAME3 = {
        "name": "field",
    }
    PACK_METADATA1 = {"name": "pack name", "itemPrefix": ["pack prefix"]}
    PACK_METADATA2 = {"name": "pack name"}
    PACK_METADATA3 = {"name": "Pack Name"}

    INPUTS_NAMES2 = [
        (FIELD_NAME1, PACK_METADATA1, False),
        (FIELD_NAME1, PACK_METADATA2, True),
        (FIELD_NAME2, PACK_METADATA1, True),
        (FIELD_NAME2, PACK_METADATA2, False),
        (FIELD_NAME3, PACK_METADATA1, False),
        (FIELD_NAME1, PACK_METADATA3, False),
    ]

    @pytest.mark.parametrize("current_file,pack_metadata, answer", INPUTS_NAMES2)
    def test_is_valid_name_prefix(self, current_file, pack_metadata, answer, mocker):
        """
        Given
        - A set of indicator fields

        When
        - Running is_valid_incident_field_name_prefix on it.

        Then
        - Ensure validate fails when the field name does not start with the pack name prefix.
        """
        from demisto_sdk.commands.common.hook_validations import field_base_validator

        with patch.object(StructureValidator, "__init__", lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = "master"
            structure.branch_name = ""
            structure.specific_validations = None
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            mocker.patch.object(
                field_base_validator, "get_pack_metadata", return_value=pack_metadata
            )
            assert validator.is_valid_field_name_prefix() == answer

    IS_VALID_FROM_VERSION_FIELD = [
        (Version("5.5.0"), "5.5.0", True),
        (Version("5.5.0"), "6.0.0", True),
        (Version("6.0.0"), "6.0.0", True),
        (Version("6.0.0"), "6.1.0", True),
        (Version("6.2.0"), "6.0.0", False),
        (Version("6.5.0"), "6.0.0", False),
        (Version("6.5.0"), "6.0.0", False),
    ]

    @pytest.mark.parametrize(
        "min_version, from_version, expected", IS_VALID_FROM_VERSION_FIELD
    )
    def test_is_valid_from_version_field(
        self, pack, min_version: Version, from_version: str, expected: bool
    ):
        """
        Given
        - A field.

        When
        - Validating the expected version is meeting the expected minimal version.

        Then
        - Ensure the expected bool is returned according to whether the condition above is satisfied.
        """
        indicator_field = pack.create_indicator_field(
            "incident_1", {"type": "html", "fromVersion": from_version}
        )
        structure = StructureValidator(indicator_field.path)
        validator = FieldBaseValidator(structure, set(), set())
        assert (
            validator.is_valid_from_version_field(
                min_version, reason_for_min_version=""
            )
            == expected
        )

    @pytest.mark.parametrize(
        "incident_content, expected_results",
        [
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": [""],
                },
                False,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": ["", "option 1", ""],
                },
                False,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": ["", "option 1"],
                },
                True,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": [],
                },
                True,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": None,
                },
                True,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": [""],
                },
                False,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": ["option 1", "option 2"],
                },
                True,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": ["", "option 1"],
                },
                False,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": [],
                },
                True,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_incident",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INCIDENT_GROUP_NUMBER,
                    "selectValues": None,
                },
                True,
            ),
        ],
    )
    def test_validate_no_empty_selected_values_value_incident(
        self, pack, incident_content, expected_results
    ):
        """
        Given
        - An incident field content and expected results.
        - Case 1: singleSelect type incident field with only empty value in the selectValues field.
        - Case 2: singleSelect type incident field with two empty values and a none-empty variable in the selectValues field.
        - Case 3: singleSelect type incident field with one empty value and a none-empty variable in the selectValues field.
        - Case 4: singleSelect type incident field with an empty list in the selectValues field.
        - Case 5: singleSelect type incident field with selectValues field set to None.
        - Case 6: multiSelect type incident field with only empty value in the selectValues field.
        - Case 7: multiSelect type incident field with two none-empty variables in the selectValues field.
        - Case 8: multiSelect type incident field with one empty value and a none-empty variable in the selectValues field.
        - Case 9: multiSelect type incident field with an empty list in the selectValues field.
        - Case 10: multiSelect type incident field with selectValues field set to None.

        When
        - Validating its selectValues do no contain empty values.

        Then
        - Ensure the right result is returned.
        """
        incident_field = pack.create_incident_field(
            "incident_1",
            incident_content,
        )
        structure = StructureValidator(incident_field.path)
        validator = FieldBaseValidator(structure, {"some-type"}, set())
        assert validator.does_not_have_empty_select_values() is expected_results

    @pytest.mark.parametrize(
        "indicator_content, expected_results",
        [
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": [""],
                },
                False,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": ["", "option 1", ""],
                },
                False,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": ["", "option 1"],
                },
                True,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": [],
                },
                True,
            ),
            (
                {
                    "type": "singleSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": None,
                },
                True,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": [""],
                },
                False,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": ["option 1", "option 2"],
                },
                True,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": ["", "option 1"],
                },
                False,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": [],
                },
                True,
            ),
            (
                {
                    "type": "multiSelect",
                    "cliName": "test_indicator",
                    "version": -1,
                    "fromVersion": "5.0.0",
                    "content": True,
                    "group": INDICATOR_GROUP_NUMBER,
                    "selectValues": None,
                },
                True,
            ),
        ],
    )
    def test_validate_no_empty_selected_values_value_indicator(
        self, pack, indicator_content, expected_results
    ):
        """
        Given
        - An indicator field content and expected results.
        - Case 1: singleSelect type indicator field with only empty value in the selectValues field.
        - Case 2: singleSelect type indicator field with two empty values and a none-empty variable in the selectValues field.
        - Case 3: singleSelect type indicator field with one empty value and a none-empty variable in the selectValues field.
        - Case 4: singleSelect type indicator field with an empty list in the selectValues field.
        - Case 5: singleSelect type indicator field with selectValues field set to None.
        - Case 6: multiSelect type indicator field with only empty value in the selectValues field.
        - Case 7: multiSelect type indicator field with two none-empty variables in the selectValues field.
        - Case 8: multiSelect type indicator field with one empty value and a none-empty variable in the selectValues field.
        - Case 9: multiSelect type indicator field with an empty list in the selectValues field.
        - Case 10: multiSelect type indicator field with selectValues field set to None.

        When
        - Validating its selectValues do no contain empty values.

        Then
        - Ensure the right result is returned.
        """
        indicator_field = pack.create_indicator_field(
            "ind_1",
            indicator_content,
        )
        structure = StructureValidator(indicator_field.path)
        validator = FieldBaseValidator(structure, {"some-type"}, set())
        assert validator.does_not_have_empty_select_values() is expected_results

    @pytest.mark.parametrize(
        "marketplaces, expected",
        [
            (["xsoar", "invalid_market"], False),
            (["invalid_market"], False),
            (["xsoar"], True),
            (None, True),
        ],
    )
    def test_is_valid_marketplaces_in_aliased_field(
        self, pack, marketplaces: List[str], expected: bool
    ):
        """
        Given
        - A field with aliases values.

        When
        - Validating the aliased fields are valid.

        Then
        - Ensure the expected bool is returned according to whether the marketplaces of the aliased fileds are valid.
        """

        tested_field = pack.create_incident_field(
            "tested_field", {"Aliases": [{"cliName": "aliased_field"}]}
        )
        incident_aliased_field = {
            "name": "incident_aliased_field",
            "cliName": "aliasedfield",
        }
        if marketplaces:
            incident_aliased_field["marketplaces"] = marketplaces

        mocked_id_set = {
            "IncidentFields": [{"incident_aliased_field": incident_aliased_field}]
        }
        structure = StructureValidator(tested_field.path)
        validator = FieldBaseValidator(
            structure, set(), set(), id_set_file=mocked_id_set
        )
        assert validator.is_aliased_fields_are_valid() == expected

    @pytest.mark.parametrize(
        "aliases, expected",
        [
            (["test", "aliased_field"], False),
            ([], True),
        ],
    )
    def test_is_inner_alias_in_aliased_field(self, pack, aliases: list, expected: bool):
        """
        Given
        - A field with aliases values.

        When
        - Validating the aliased fields are valid.

        Then
        - Ensure the expected bool is returned according to whether the aliased field have inner alias or not.
        """

        tested_field = pack.create_incident_field(
            "tested_field", {"Aliases": [{"cliName": "aliasedfield"}]}
        )

        incident_aliased_field = {
            "name": "incident_aliasedfield",
            "cliname": "aliasedfield",
        }
        if aliases:
            incident_aliased_field["aliases"] = aliases

        mocked_id_set = {
            "IncidentFields": [{"incident_aliasedfield": incident_aliased_field}]
        }
        structure = StructureValidator(tested_field.path)
        validator = FieldBaseValidator(
            structure, set(), set(), id_set_file=mocked_id_set
        )
        assert validator.is_aliased_fields_are_valid() == expected

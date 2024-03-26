import os
from typing import Dict

import pytest

from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import (
    PACK_METADATA_NAME,
    PACK_METADATA_SUPPORT,
    BlockingValidationFailureException,
    PackUniqueFilesValidator,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path


class TestPackMetadataValidator:
    FILES_PATH = os.path.normpath(
        os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
    )

    @pytest.fixture()
    def deprecated_pack(self, request, pack):
        """
        Creates a pack containing either integrations/playbooks/scripts which can be deprecated or not.
        In addition returns whether a pack should be hidden.
        """
        (
            integrations_data,
            scripts_data,
            playbooks_data,
            should_pack_be_deprecated,
        ) = request.param

        for name, should_deprecate in integrations_data:
            integration = pack.create_integration(name=name)
            integration.yml.update({"deprecated": should_deprecate})

        for name, should_deprecate in scripts_data:
            script = pack.create_script(name=name)
            script.yml.update({"deprecated": should_deprecate})

        for name, should_deprecate in playbooks_data:
            playbook = pack.create_playbook(name=name)
            playbook.yml.update({"deprecated": should_deprecate})

        return pack, should_pack_be_deprecated

    @pytest.mark.parametrize(
        "metadata",
        [
            os.path.join(FILES_PATH, "pack_metadata__valid.json"),
            os.path.join(FILES_PATH, "pack_metadata__valid_module.json"),
            os.path.join(FILES_PATH, "pack_metadata__valid__community.json"),
        ],
    )
    def test_metadata_validator_valid(self, mocker, metadata):
        mocker.patch(
            "demisto_sdk.commands.common.hook_validations.pack_unique_files.get_current_categories",
            return_value=["Data Enrichment & Threat Intelligence"],
        )
        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(
            PackUniqueFilesValidator,
            "_read_file_content",
            return_value=TestPackMetadataValidator.read_file(metadata),
        )
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_pack_file_exists", return_value=True
        )

        validator = PackUniqueFilesValidator("fake")
        assert validator.validate_pack_meta_file()

    @pytest.mark.parametrize(
        "metadata",
        [
            os.path.join(FILES_PATH, "pack_metadata_invalid_price.json"),
            os.path.join(FILES_PATH, "pack_metadata_invalid_dependencies.json"),
            os.path.join(FILES_PATH, "pack_metadata_list_dependencies.json"),
            os.path.join(FILES_PATH, "pack_metadata_empty_categories.json"),
            os.path.join(FILES_PATH, "pack_metadata_invalid_category.json"),
            os.path.join(FILES_PATH, "pack_metadata_invalid_keywords.json"),
            os.path.join(FILES_PATH, "pack_metadata_invalid_tags.json"),
            os.path.join(FILES_PATH, "pack_metadata_invalid_format_version.json"),
            os.path.join(FILES_PATH, "pack_metadata__invalid_module.json"),
            os.path.join(FILES_PATH, "pack_metadata__module_non_xsiam.json"),
        ],
    )
    def test_metadata_validator_invalid__non_breaking(self, mocker, metadata):
        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(
            PackUniqueFilesValidator,
            "_read_file_content",
            return_value=TestPackMetadataValidator.read_file(metadata),
        )
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_pack_file_exists", return_value=True
        )
        mocker.patch.object(BaseValidator, "check_file_flags", return_value="")
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_integration_pack", return_value=True
        )

        validator = PackUniqueFilesValidator("fake")
        assert not validator.validate_pack_meta_file()

    @pytest.mark.parametrize(
        "metadata",
        [
            os.path.join(FILES_PATH, "pack_metadata_missing_fields.json"),
            os.path.join(FILES_PATH, "pack_metadata_list.json"),
            os.path.join(FILES_PATH, "pack_metadata_short_name.json"),
            os.path.join(FILES_PATH, "pack_metadata_name_start_lower.json"),
            os.path.join(FILES_PATH, "pack_metadata_name_start_incorrect.json"),
            os.path.join(FILES_PATH, "pack_metadata_pack_in_name.json"),
        ],
    )
    def test_metadata_validator_invalid__breaking(self, mocker, metadata):
        """
        Given
                A pack metadata file with invalid contents that should halt validations
        When
                Calling validate_pack_meta_file
        Then
                Ensure BlockingValidationFailureException is raised
        """
        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(
            PackUniqueFilesValidator,
            "_read_file_content",
            return_value=TestPackMetadataValidator.read_file(metadata),
        )
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_pack_file_exists", return_value=True
        )
        mocker.patch.object(BaseValidator, "check_file_flags", return_value="")

        validator = PackUniqueFilesValidator("fake")
        with pytest.raises(BlockingValidationFailureException):
            assert not validator.validate_pack_meta_file()

    VALIDATE_PACK_NAME_INPUTS = [
        ({PACK_METADATA_NAME: "fill mandatory field"}, False),
        ({PACK_METADATA_NAME: "A"}, False),
        ({PACK_METADATA_NAME: "notCapitalized"}, False),
        (
            {
                PACK_METADATA_NAME: "BitcoinAbuse (Community)",
                PACK_METADATA_SUPPORT: "community",
            },
            False,
        ),
        ({PACK_METADATA_NAME: "BitcoinAbuse"}, True),
    ]

    @pytest.mark.parametrize("metadata_content, expected", VALIDATE_PACK_NAME_INPUTS)
    def test_validate_pack_name(self, metadata_content: Dict, expected: bool, mocker):
        """
        Given:
        - Metadata JSON pack file content.

        When:
        - Validating if pack name is valid.

        Then:
        - Ensure expected result is returned.
        """
        validator = PackUniqueFilesValidator("fake")
        mocker.patch.object(validator, "_add_error", return_value=True)
        assert validator.validate_pack_name(metadata_content) == expected

    @staticmethod
    def read_file(file_):
        with open(file_, encoding="utf-8") as data:
            return data.read()

    def test_metadata_not_dict(self, mocker):
        """
        Given:
        - Metadata file whom structure is not a dict

        When:
        - Validating metadata structure.

        Then:
        - Ensure false is returned, and a BlockingValidationFailureException is raised.
        """
        mocker.patch.object(
            PackUniqueFilesValidator, "_read_metadata_content", return_value={"a", "b"}
        )
        validator = PackUniqueFilesValidator("fake")
        mocker.patch.object(validator, "_add_error")
        with pytest.raises(BlockingValidationFailureException):
            assert not validator._is_pack_meta_file_structure_valid()

    def test_metadata_validator_empty_categories(self, mocker):
        metadata = os.path.join(
            self.__class__.FILES_PATH, "pack_metadata_empty_categories.json"
        )
        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(
            PackUniqueFilesValidator,
            "_read_file_content",
            return_value=TestPackMetadataValidator.read_file(metadata),
        )
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_pack_file_exists", return_value=True
        )
        mocker.patch.object(BaseValidator, "check_file_flags", return_value="")
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_integration_pack", return_value=True
        )
        validator = PackUniqueFilesValidator("fake")
        assert not validator.validate_pack_meta_file()
        assert (
            "[PA129] - pack_metadata.json - Missing categories"
            in validator.get_errors()
        )

    def test_is_integration_pack(self, pack):
        """
        Given:
            - A pack with an integration to validate.

        When:
            - Calling _is_integration_pack() method.

        Then:
            - Ensure true is returned, indicates the pack contains integration.
        """
        pack.create_integration("test")
        validator = PackUniqueFilesValidator(pack.name, pack_path=pack.path)
        assert validator._is_integration_pack()

    def test_metadata_validator_invalid_version_add_error(self, mocker):
        """
        Given:
            - pack metadata.json file with wrong version type

        When:
            - validating meta data structure

        Then:
            - Ensure false is returned and the correct error is added to the validation object error list
        """
        metadata = os.path.join(
            self.FILES_PATH, "pack_metadata_invalid_format_version.json"
        )
        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(
            PackUniqueFilesValidator,
            "_read_file_content",
            return_value=TestPackMetadataValidator.read_file(metadata),
        )
        mocker.patch.object(
            PackUniqueFilesValidator, "_is_pack_file_exists", return_value=True
        )
        mocker.patch.object(BaseValidator, "check_file_flags", return_value="")

        validator = PackUniqueFilesValidator("fake")
        assert not validator.validate_pack_meta_file()
        assert (
            "[PA130] - Pack metadata version format is not valid. Please fill in a valid format (example: 0.0.0)"
            in validator.get_errors()
        )

    # checks for the version
    version_checks = [
        ("1.1.1", True),
        ("12.1.5", True),
        ("4.4.16", True),
        ("blabla", False),
        ("1.2", False),
        ("0.", False),
        ("1-2-1", False),
    ]

    @pytest.mark.parametrize("version,expected", version_checks)
    def test_is_version_format(self, version, expected):
        """
        Given:
            - A version to be checked by the _is_version_format function

        When:
            - Validating meta data structure.

        Then:
            - return True if the version is in the correct format and False otherwise
        """
        validator = PackUniqueFilesValidator("fake")
        assert validator._is_version_format_valid(version) == expected

    @pytest.mark.parametrize(
        "deprecated_pack",
        [
            ([("integration-1", True), ("integration-2", True)], [], [], True),
            ([("integration-1", True), ("integration-2", False)], [], [], False),
            (
                [("integration-1", False), ("integration-2", True)],
                [("script-1", True)],
                [],
                False,
            ),
            ([], [("script-1", True), ("script-2", True)], [], True),
            (
                [],
                [("script-1", True), ("script-2", False)],
                [("playbook-1", True)],
                False,
            ),
            (
                [],
                [("script-1", True)],
                [("playbook-1", True), ("playbook-1", False)],
                False,
            ),
            ([], [], [("playbook-1", True), ("playbook-2", True)], True),
            (
                [],
                [("script-1", True), ("script-2", True)],
                [("playbook-1", True)],
                True,
            ),
            (
                [("integration-1", True), ("integration-2", False)],
                [("script-1", True), ("script-2", True)],
                [("playbook-1", True)],
                False,
            ),
            (
                [("integration-1", True), ("integration-2", True)],
                [("script-1", True), ("script-2", True)],
                [("playbook-1", True)],
                True,
            ),
            (
                [("integration-1", True), ("integration-2", True)],
                [("script-1", True), ("script-2", True)],
                [("playbook-1", False)],
                False,
            ),
            (
                [("integration-1", True), ("integration-2", True)],
                [("script-1", False), ("script-2", True)],
                [("playbook-1", True)],
                False,
            ),
            ([], [], [], False),
        ],
        indirect=True,
    )
    def test_should_pack_be_deprecated(self, deprecated_pack):
        """
        Given:
            - Case 1: all integrations are deprecated and there aren't any scripts or playbooks in the pack.
            - Case 2: not all the integrations are deprecated and there aren't any scripts or playbooks in the pack.
            - Case 3: not all the integrations are deprecated and there are deprecated scripts and no playbooks in pack.
            - Case 4: no integrations or playbooks, but scripts which are all deprecated in the pack.
            - Case 5: no integrations, but scripts which are not all deprecated and a
                    playbook which is deprecated in the pack.
            - Case 6: no integrations, but scripts which are all deprecated and a playbook which is not deprecated.
            - Case 7: no integrations or scripts, but playbooks which are all deprecated in the pack.
            - Case 8: no integrations, but playbooks and scripts which are all deprecated in the pack.
            - Case 9: integrations which are not all
                deprecated and playbooks and scripts which are all deprecated in the pack.
            - Case 10: all integrations, playbooks and scripts are deprecated.
            - Case 11: all integrations and scripts are deprecated but the playbook is not deprecated.
            - Case 12: all integrations and playbooks are deprecated but not all the scripts are deprecated.
            - Case 13: there aren't any integrations/playbooks/scripts.

        When:
            - validating whether a pack should be hidden (True if it should be hidden, False if not)

        Then:
            - Case 1: pack should be deprecated.
            - Case 2: pack should not be deprecated.
            - Case 3: pack should not be deprecated.
            - Case 4: pack should be deprecated.
            - Case 5: pack should not be deprecated.
            - Case 6: pack should not be deprecated.
            - Case 7: pack should be deprecated.
            - Case 8: pack should be deprecated.
            - Case 9: pack should not be deprecated.
            - case 10: pack should be deprecated.
            - case 11: pack should not be deprecated.
            - case 12: pack should not be deprecated.
            - case 13: pack should not be deprecated (as there aren't any deprecated content items)
        """
        pack, should_pack_be_deprecated = deprecated_pack
        validator = PackUniqueFilesValidator(pack.path)
        assert validator.should_pack_be_deprecated() == should_pack_be_deprecated

    VALID_CATEGORIES_LIST = ["Endpoint", "File Integrity Management"]

    @pytest.mark.parametrize(
        "metadata_content, expected_results, valid_list_mock",
        [
            ({"categories": ["Endpoint"]}, True, VALID_CATEGORIES_LIST),
            ({"categories": ["Analytics & SIEMM"]}, False, VALID_CATEGORIES_LIST),
            (
                {"categories": ["Endpoint", "File Integrity Management"]},
                False,
                VALID_CATEGORIES_LIST,
            ),
            (
                {"categories": ["Analytics & SIEMM", "random category"]},
                False,
                VALID_CATEGORIES_LIST,
            ),
            (
                {"categories": ["Analytics & SIEMM", "Endpoint"]},
                False,
                VALID_CATEGORIES_LIST,
            ),
        ],
    )
    def test_is_categories_field_match_standard(
        self, mocker, metadata_content, expected_results, valid_list_mock
    ):
        """
        Given:
            - A pack metadata content and a list of approved categories.
            - case 1: pack metadata content with one valid category and the valid categories list.
            - case 2: pack metadata content with one invalid category and the valid categories list.
            - case 3: pack metadata content with two valid categories and the valid categories list.
            - case 4: pack metadata content with two invalid categories and the valid categories list.
            - case 5: pack metadata content with one invalid category and one valid category, and the valid categories list.

        When:
            - running is_categories_field_match_standard function.

        Then:
            - Ensure that the categories field was validated correctly.
            - case 1: Should return True.
            - case 2: Should return False.
            - case 3: Should return False.
            - case 4: Should return False.
            - case 5: Should return False.
        """
        mocker.patch(
            "demisto_sdk.commands.common.hook_validations.pack_unique_files.get_current_categories",
            return_value=valid_list_mock,
        )
        validator = PackUniqueFilesValidator("test")
        validator.metadata_content = metadata_content
        assert validator.is_categories_field_match_standard() is expected_results

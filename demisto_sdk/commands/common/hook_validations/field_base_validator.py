"""
This module is designed to validate the correctness of incident field entities in content.
"""

import re
from enum import IntEnum
from typing import List, Set

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_core_pack_list,
    get_pack_metadata,
    get_pack_name,
)

# Cortex XSOAR is using a Bleve DB, those keys cannot be the cliName
BleveMapping = {
    1: [
        "id",
        "shardid",
        "modified",
        "incidentid",
        "entryid",
        "description",
        "tags",
        "tagsraw",
        "occurred",
        "markeddate",
        "fetched",
        "taskid",
        "markedby",
        "roles",
        "previousroles",
        "hasrole",
        "dbotcreatedBy",
    ],
}

FIELD_CLI_NAME_VALIDATION_REGEX = r"[0-9a-z]+$"


class GroupFieldTypes(IntEnum):
    INCIDENT_FIELD = 0
    EVIDENCE_FIELD = 1
    INDICATOR_FIELD = 2

    @classmethod
    def is_valid_group(cls, group):
        return group in [group.value for group in cls]


class FieldBaseValidator(ContentEntityValidator):
    """IncidentFieldValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """

    def __init__(
        self,
        structure_validator,
        field_types: Set[str],
        prohibited_cli_names: Set[str],
        ignored_errors=False,
        json_file_path=None,
        id_set_file=None,
        **kwargs,
    ):
        super().__init__(
            structure_validator,
            ignored_errors,
            json_file_path=json_file_path,
            **kwargs,
        )
        self.field_types = field_types
        self.prohibited_cli_names = prohibited_cli_names
        self.id_set_file = id_set_file

    def is_backward_compatible(self):
        """
        Check whether the field is backward compatible or not.
        Returns:
            (bool): True if field is backward compatible, false otherwise.
        """
        if not self.old_file:
            return True

        is_bc_broke = any(
            [
                not super().is_backward_compatible(),
                self.is_changed_type(),
                self.is_changed_from_version(),
            ]
        )

        return not is_bc_broke

    def is_valid_file(
        self, validate_rn=True, is_new_file=False, use_git=False, is_added_file=False
    ):
        """Check whether the Incident Field is valid or not"""
        answers = [
            super().is_valid_file(validate_rn),
            self.is_valid_type(),
            self.is_valid_group(),
            self.is_valid_content_flag(),
            self.is_valid_system_flag(),
            self.is_valid_cli_name(),
            self.is_valid_version(),
            self.is_valid_required(),
            self.does_not_have_empty_select_values(),
            self.is_aliased_fields_are_valid(),
        ]

        core_packs_list = get_core_pack_list()

        pack = get_pack_name(self.file_path)
        is_core = pack in core_packs_list
        if is_core:
            answers.append(self.is_valid_name())
        if is_new_file and use_git:
            answers.append(self.is_valid_field_name_prefix())
        if is_added_file:
            answers.append(self.is_valid_unsearchable_key())
        return all(answers)

    @error_codes("IF100")
    def is_valid_name(self):
        """Validate that the name and cliName does not contain any potential incident synonyms."""
        name = self.current_file.get("name", "")
        bad_words = {
            "incident",
            "case",
            "alert",
            "event",
            "playbook",
            "ticket",
            "issue",
            "incidents",
            "cases",
            "alerts",
            "events",
            "playbooks",
            "tickets",
            "issues",
        }
        found_words = []
        for word in name.split():
            if word.lower() in bad_words:
                found_words.append(word)

        if found_words:
            error_message, error_code = Errors.invalid_incident_field_name(found_words)
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_server_allowlist_fix(words=found_words),
            ):
                return False

        return True

    @error_codes("IF101")
    def is_valid_content_flag(self):
        """
        Validates that the field is marked as content.
        Returns:
            (bool): True if field is marked as content, false otherwise.
        """
        if not self.current_file.get("content"):
            error_message, error_code = Errors.invalid_field_content_key_value()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False
        return True

    @error_codes("IF102")
    def is_valid_system_flag(self):
        """
        Validates that system flag is false.
        Returns:
            (bool): True if system flag is set to false, false otherwise.
        """
        if self.current_file.get("system"):
            error_message, error_code = Errors.invalid_incident_field_system_key_value()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False
        return True

    def is_valid_version(self) -> bool:
        """
        Checks whether version is valid.
        Returns:
            (bool): True of version is valid, false otherwise.
        """
        return super()._is_valid_version()

    @error_codes("IF103")
    def is_valid_type(self) -> bool:
        """
        Checks if given field type is valid.
        Returns:
            (bool): True if valid, false otherwise.
        """
        if self.current_file.get("type") not in self.field_types:
            error_message, error_code = Errors.invalid_field_type(
                self.current_file.get("type"), self.field_types
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IF104")
    def is_valid_group(self) -> bool:
        """
        Checks if given group number is a valid number.
        Returns:
            (bool): True if group number is valid, false otherwise.
        """
        group = self.current_file.get("group")
        if GroupFieldTypes.is_valid_group(group):
            return True
        error_message, error_code = Errors.invalid_field_group_value(group)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False
        return True

    def is_valid_cli_name(self) -> bool:
        """
        Checks if given CLI name is valid.
        1) Checks that the CLI name matches the CLI regex.
        2) Checks that the CLI name does not use a reserved word from Bleve mapping.
        Returns:
            (bool): True if all tests passes, false otherwise.
        """
        return (
            self.is_cli_name_is_builtin_key()
            and self.is_matching_cli_name_regex()
            and self.does_cli_name_match_id()
        )

    def does_cli_name_match_id(self):
        """
        Checks if the field cliName matched to id.
        Returns:
            (bool): True if cliName matched to id, False otherwise.
        """
        cli_name = self.current_file["cliName"]
        _id = self.current_file.get("id", "").lower().replace("_", "").replace("-", "")
        if _id.startswith("incident"):
            cli_name_expected = _id[len("incident") :]
        elif _id.startswith("indicator"):
            cli_name_expected = _id[len("indicator") :]
        else:
            return True
        if cli_name != cli_name_expected and cli_name != _id:
            error_message, error_code = Errors.cli_name_and_id_do_not_match(_id)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IF105")
    def is_matching_cli_name_regex(self) -> bool:
        """
        Checks if the field cliName matches the expected cliName regex.
        Returns:
            (bool): True if matches the expected `FIELD_CLI_NAME_VALIDATION_REGEX` regex, false otherwise.
        """
        cliname = self.current_file.get("cliName")
        if re.fullmatch(FIELD_CLI_NAME_VALIDATION_REGEX, cliname):  # type: ignore
            return True
        error_message, error_code = Errors.invalid_incident_field_cli_name_regex(
            FIELD_CLI_NAME_VALIDATION_REGEX
        )
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False
        return True

    @error_codes("IF106")
    def is_cli_name_is_builtin_key(self) -> bool:
        """
        Checks if given CLI name is a reserved word that cannot be used due to Bleve mapping.
        Returns:
            (bool): False if CLI name is a reserved word, true otherwise.
        """
        cli_name = self.current_file.get("cliName")
        is_valid = cli_name not in self.prohibited_cli_names
        if not is_valid:
            error_message, error_code = Errors.invalid_incident_field_cli_name_value(
                cli_name
            )
            if not self.handle_error(
                error_message, error_code, file_path=self.file_path
            ):
                is_valid = True
        return is_valid

    @error_codes("IF109")
    def is_valid_required(self) -> bool:
        """Validate that the incident field is not required."""
        # due to a current platform limitation, incident fields can not be set to required
        # after it will be fixed, need to validate that required field are not associated to all incident types
        # as can be seen in this pr: https://github.com/demisto/content/pull/5682
        if self.current_file.get("required"):
            error_message, error_code = Errors.new_field_required()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IF110")
    def is_changed_from_version(self) -> bool:
        """
        Checks if given from version field value has been changed.
        Returns:
            (bool): True if from version field was changed, false otherwise.
        """
        is_from_version_changed = False
        old_from_version = self.old_file.get("fromVersion", None)
        if old_from_version:
            current_from_version = self.current_file.get("fromVersion", None)
            if old_from_version != current_from_version:
                error_message, error_code = Errors.from_version_modified_after_rename()
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    is_from_version_changed = True

        return is_from_version_changed

    @error_codes("IF111")
    def is_changed_type(self) -> bool:
        """
        Validates that the field type was not changed.
        Returns:
            (bool): True if type was changed, false otherwise.
        """
        is_type_changed = False
        current_type = self.current_file.get("type", "")
        if self.old_file:
            old_type = self.old_file.get("type", {})
            if old_type and old_type != current_type:
                error_message, error_code = Errors.incident_field_type_change()
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    is_type_changed = True

        return is_type_changed

    @error_codes("IF113")
    def is_valid_field_name_prefix(self) -> bool:
        """
        Validate that a field name starts with its pack name or one of the itemPrefixes from pack metadata.
        Returns:
            (bool): True if field name starts with `itemPrefixes` or pack name, false otherwise.
        """
        ignored_packs = ["Common Types", "Core Alert Fields"]
        pack_metadata = get_pack_metadata(self.file_path)
        pack_name = pack_metadata.get("name")
        name_prefixes = (
            pack_metadata.get("itemPrefix", [])
            if pack_metadata.get("itemPrefix")
            else [pack_name]
        )
        field_name = self.current_file.get("name", "")
        if pack_name and pack_name not in ignored_packs:
            for prefix in name_prefixes:
                if self.current_file.get("name", "").startswith(prefix):
                    return True

            error_message, error_code = Errors.invalid_incident_field_prefix(field_name)
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix_field_name(
                    field_name, pack_prefix=name_prefixes[0]
                ),
            ):
                return False

        return True

    @error_codes("IF115")
    def is_valid_unsearchable_key(self) -> bool:
        """
        Validate that the unsearchable key is true.
        Returns:
            bool. Whether the file's unsearchable key is set to true.
        """
        if not self.current_file.get("unsearchable", True):
            (
                error_message,
                error_code,
            ) = Errors.unsearchable_key_should_be_true_incident_field()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False
        return True

    @error_codes("IF112")
    def is_valid_from_version_field(
        self, min_from_version: Version, reason_for_min_version: str
    ):
        """
        Validates that the from version field is set to the expected minimum.
        This function is used for cases when:
        1) Indicator field has the grid type, where the from version field needs to be set to 5.5.0 at least.
        2) Indicator field has the html type, where the from version field needs to be set to 6.1.0 at least.
        Args:
            min_from_version (Version): Minimum from version to the field.
            reason_for_min_version (str): Reason for the requested min version. Used for better error message.

        Returns:
            (bool): True if from version is equal or greater than `min_from_version`, false otherwise.
        """
        current_version = Version(
            self.current_file.get("fromVersion", DEFAULT_CONTENT_ITEM_FROM_VERSION)
        )
        if current_version < min_from_version:
            error_message, error_code = Errors.field_version_is_not_correct(
                current_version, min_from_version, reason_for_min_version
            )
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                warning=self.structure_validator.quiet_bc,
            ):
                return False
        return True

    @error_codes("IF116")
    def does_not_have_empty_select_values(self) -> bool:
        """
        Due to UI issues, we cannot allow empty values for selectValues field.
        Returns:
            (bool): True if selectValues does not have empty values, false if contains empty value.
        """
        error_message, error_code = "", ""
        select_values = self.current_file.get("selectValues") or []
        empty_string_count = sum(select_value == "" for select_value in select_values)
        if self.current_file.get("type") == "singleSelect":
            if (
                empty_string_count and len(select_values) == 1
            ) or empty_string_count > 1:
                (
                    error_message,
                    error_code,
                ) = Errors.select_values_cannot_contain_multiple_or_only_empty_values_in_single_select_types()
        else:
            if empty_string_count:
                (
                    error_message,
                    error_code,
                ) = Errors.select_values_cannot_contain_empty_values_in_multi_select_types()
        if error_code and error_message:
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                warning=self.structure_validator.quiet_bc,
            ):
                return False
        return True

    @error_codes("IF117,IF118")
    def is_aliased_fields_are_valid(self) -> bool:
        """
        Validates that the aliased fields (fields that appear as Aliases in another field) are valid.
        invalid aliased fields are
        1. fields that are in another field's Aliases list, and present in the same marketplace of that field.
        2. fields that are in another field's Aliases list, and also contain Aliases (nested aliasing)

        Returns:
            (bool): True if aliased fields are valid.
        """

        if not self.id_set_file:
            logger.warning(
                "<yellow>Validate will skip since an id set file was not provided</yellow>"
            )
            return True

        aliases = self.current_file.get("Aliases", [])
        if not aliases:
            return True

        is_valid = True
        validators_and_error_generators = [
            (
                self.is_alias_has_invalid_marketplaces,
                Errors.invalid_marketplaces_in_alias,
            ),
            (self.is_alias_has_inner_alias, Errors.aliases_with_inner_alias),
        ]
        for validator, error_generator in validators_and_error_generators:
            invalid_aliases = [
                alias.get("cliname")
                for alias in self._get_incident_fields_by_aliases(aliases)
                if validator(alias)
            ]
            if invalid_aliases:
                error_message, error_code = error_generator(invalid_aliases)
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    is_valid = False

        return is_valid

    def _get_incident_fields_by_aliases(self, aliases: List[dict]):
        """Get from the id_set the actual fields for the given aliases

        Args:
            aliases (list): The alias list.

        Returns:
            A generator that generates a tuple with the incident field for each alias in the given list.
        """
        alias_ids: set = {f'incident_{alias.get("cliName")}' for alias in aliases}
        incident_field_list: list = self.id_set_file.get("IncidentFields")

        for incident_field in incident_field_list:
            field_id = list(incident_field.keys())[0]
            if field_id in alias_ids:
                aliased_field = incident_field[field_id]
                yield aliased_field

    def is_alias_has_invalid_marketplaces(self, aliased_field: dict) -> bool:
        return aliased_field.get("marketplaces", [MarketplaceVersions.XSOAR.value]) != [
            MarketplaceVersions.XSOAR.value
        ]

    def is_alias_has_inner_alias(self, aliased_field: dict) -> bool:
        return aliased_field is not None and "aliases" in aliased_field

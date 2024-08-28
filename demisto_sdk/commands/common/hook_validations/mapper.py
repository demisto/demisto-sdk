from typing import Dict, List

from packaging.version import Version

from demisto_sdk.commands.common.constants import LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_all_incident_and_indicator_fields_from_id_set,
    get_invalid_incident_fields_from_mapper,
)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION = "6.0.0"
VALID_TYPE_INCOMING = "mapping-incoming"
VALID_TYPE_OUTGOING = "mapping-outgoing"


class MapperValidator(ContentEntityValidator):
    def __init__(
        self,
        structure_validator,
        ignored_errors=None,
        json_file_path=None,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
        )
        self.from_version = ""
        self.to_version = ""

    def is_valid_mapper(self, validate_rn=True, id_set_file=None, is_circle=False):
        """Checks whether the mapper is valid or not.

        Returns:
            bool. True if mapper is valid, else False.
        """
        return all(
            [
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_valid_from_version(),
                self.is_valid_to_version(),
                self.is_to_version_higher_from_version(),
                self.is_valid_type(),
                self.is_incident_field_exist(id_set_file, is_circle),
                self.is_id_equals_name(),
            ]
        )

    def is_valid_version(self):
        """Checks if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_backward_compatible(self) -> bool:
        """Check whether the Mapper is backward compatible or not, update the _is_valid field to determine that"""

        answers = [
            not super().is_backward_compatible(),
            self.is_field_mapping_removed(),
        ]
        return not any(answers)

    @error_codes("MP108,MP107")
    def is_field_mapping_removed(self):
        """checks if some incidents fields or incidents types were removed"""
        old_mapper = self.old_file.get("mapping", {})
        current_mapper = self.current_file.get("mapping", {})

        old_incidents_types = {inc for inc in old_mapper}
        current_incidents_types = {inc for inc in current_mapper}
        if not old_incidents_types.issubset(current_incidents_types):
            removed_incident_types = old_incidents_types - current_incidents_types
            removed_dict = {}
            for removed in removed_incident_types:
                removed_dict[removed] = old_mapper[removed]
            error_message, error_code = Errors.removed_incident_types(removed_dict)
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                warning=self.structure_validator.quiet_bc,
            ):
                self.is_valid = False
                return True
        else:
            removed_incident_fields = {}
            for inc in old_incidents_types:
                old_incident_fields = old_mapper[inc].get("internalMapping", {}) or {}
                current_incident_fields = (
                    current_mapper[inc].get("internalMapping", {}) or {}
                )

                old_fields = {inc for inc in old_incident_fields}
                current_fields = {inc for inc in current_incident_fields}

                if not old_fields.issubset(current_fields):
                    removed_fields = old_fields - current_fields
                    removed_incident_fields[inc] = removed_fields

            if removed_incident_fields:
                error_message, error_code = Errors.changed_incident_field_in_mapper(
                    removed_incident_fields
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    warning=self.structure_validator.quiet_bc,
                ):
                    self.is_valid = False
                    return True

        return False

    @error_codes("MP100,MP103")
    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.current_file.get(
            "fromVersion", ""
        ) or self.current_file.get("fromversion")
        if from_version:
            self.from_version = from_version
            if Version(from_version) < Version(FROM_VERSION):
                error_message, error_code = Errors.invalid_from_version_in_mapper()
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=self.file_path,
                    suggested_fix=Errors.suggest_fix(self.file_path),
                ):
                    return False
        else:
            error_message, error_code = Errors.missing_from_version_in_mapper()
            if self.handle_error(
                error_message,
                error_code,
                file_path=self.file_path,
                suggested_fix=Errors.suggest_fix(self.file_path),
            ):
                return False
        return True

    @error_codes("MP101")
    def is_valid_to_version(self):
        """Checks if to version is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        to_version = self.current_file.get("toVersion", "") or self.current_file.get(
            "toversion", ""
        )
        if to_version:
            self.to_version = to_version
            if Version(to_version) < Version(FROM_VERSION):
                error_message, error_code = Errors.invalid_to_version_in_mapper()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        return True

    @error_codes("CL106")
    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version and self.from_version:
            if Version(self.to_version) <= Version(self.from_version):
                error_message, error_code = Errors.from_version_higher_to_version()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        return True

    @error_codes("MP104")
    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.current_file.get("type") not in [
            VALID_TYPE_INCOMING,
            VALID_TYPE_OUTGOING,
        ]:
            error_message, error_code = Errors.invalid_type_in_mapper()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("MP106")
    def is_incident_field_exist(
        self, id_set_file: Dict[str, List], is_circle: bool
    ) -> bool:
        """
        Check if the incident fields which are part of the mapper actually exist in the content items (id set).

        Args:
            id_set_file (dict): content of the id set file.
            is_circle (bool): whether running on circle CI or not, True if yes, False if not.

        Returns:
            bool: False if there are incident fields which are part of the mapper that do not exist in content items,
                True if there aren't.
        """
        if not is_circle:
            return True

        if not id_set_file:
            logger.info(
                "<yellow>Skipping mapper incident field validation. Could not read id_set.json.</yellow>"
            )
            return True

        content_incident_fields = (
            get_all_incident_and_indicator_fields_from_id_set(id_set_file, "mapper")
            + [field.lower() for field in BUILT_IN_FIELDS]
            + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
        )

        invalid_incident_fields = []
        mapping_type = self.current_file.get("type", {})

        mapper = self.current_file.get("mapping", {})
        for value in mapper.values():
            incident_fields = value.get("internalMapping") or {}
            invalid_incident_fields.extend(
                get_invalid_incident_fields_from_mapper(
                    mapper_incident_fields=incident_fields,
                    mapping_type=mapping_type,
                    content_fields=content_incident_fields,
                )
            )

        if invalid_incident_fields:
            error_message, error_code = Errors.invalid_incident_field_in_mapper(
                invalid_incident_fields
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_id_equals_name(self):
        """Check whether the mapper ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name("mapper")

import re
from distutils.version import LooseVersion

from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_FROM_VERSION
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)

# Checks if playbookID is a UUID format
INVALID_PLAYBOOK_ID = r"[\w\d]{8}-[\w\d]{4}-[\w\d]{4}-[\w\d]{4}-[\w\d]{12}"


class IncidentTypeValidator(ContentEntityValidator):
    """IncidentTypeValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """

    def is_backward_compatible(self):
        """Check whether the Incident Type is backward compatible or not"""
        if not self.old_file:
            return True

        is_bc_broke = any(
            [not super().is_backward_compatible(), self.is_changed_from_version()]
        )

        return not is_bc_broke

    def is_valid_incident_type(self, validate_rn=True):
        """Check whether the Incident Type is valid or not"""
        is_incident_type__valid = all(
            [
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_valid_autoextract(),
            ]
        )

        # check only on added files
        if not self.old_file:
            is_incident_type__valid = all(
                [
                    is_incident_type__valid,
                    self.is_id_equals_name(),
                    self.is_including_int_fields(),
                    self.is_valid_playbook_id(),
                ]
            )

        return is_incident_type__valid

    def is_valid_version(self) -> bool:
        """Check if a valid version.
        Returns:
            bool. Whether the version is valid or not.
        """
        return super()._is_valid_version()

    def is_id_equals_name(self) -> bool:
        """Check whether the incident Type ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name("incident_type")

    @error_codes("IF110")
    def is_changed_from_version(self) -> bool:
        """Check if fromversion has been changed.
        Returns:
            bool. Whether fromversion has been changed.
        """
        is_bc_broke = False

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
                    is_bc_broke = True
        return is_bc_broke

    @error_codes("IT100,IF108")
    def is_including_int_fields(self) -> bool:
        """Check if including required fields, only from 5.0.0.
        Returns:
            bool. Whether the included fields have a positive integer value.
        """
        is_valid = True
        fields_to_include = ["hours", "days", "weeks", "hoursR", "daysR", "weeksR"]

        try:
            from_version = self.current_file.get(
                "fromVersion", DEFAULT_CONTENT_ITEM_FROM_VERSION
            )
            if LooseVersion(from_version) >= LooseVersion("5.0.0"):
                for field in fields_to_include:
                    int_field = self.current_file.get(field, -1)
                    if not isinstance(int_field, int) or int_field < 0:
                        error_message, error_code = Errors.incident_type_integer_field(
                            field
                        )
                        if self.handle_error(
                            error_message, error_code, file_path=self.file_path
                        ):
                            is_valid = False

        except (AttributeError, ValueError):
            (
                error_message,
                error_code,
            ) = Errors.invalid_incident_field_or_type_from_version()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    @error_codes("IT101")
    def is_valid_playbook_id(self) -> bool:
        """Check if playbookId is valid
        Returns:
            bool. True if playbook ID is valid, False otherwise.
        """
        playbook_id = self.current_file.get("playbookId", "")
        if playbook_id and re.search(INVALID_PLAYBOOK_ID, playbook_id):
            error_message, error_code = Errors.incident_type_invalid_playbook_id_field()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("IT102,IT103")
    def is_valid_autoextract(self):
        """Check if extractSettings field is valid.

        Returns:
            bool. True if extractSettings is valid or empty, False otherwise
        """
        auto_extract_data = self.current_file.get("extractSettings", {})

        # no auto extraction set in incident type.
        if not auto_extract_data:
            return True

        auto_extract_fields = auto_extract_data.get("fieldCliNameToExtractSettings")
        auto_extract_mode = auto_extract_data.get("mode")

        is_valid = True

        if auto_extract_fields:
            invalid_incident_fields = []
            for incident_field, extracted_settings in auto_extract_fields.items():
                extracting_all = extracted_settings.get("isExtractingAllIndicatorTypes")
                extract_as_is = extracted_settings.get("extractAsIsIndicatorTypeId")
                extracted_indicator_types = extracted_settings.get(
                    "extractIndicatorTypesIDs"
                )

                # General format check.
                if (
                    type(extracting_all) != bool
                    or type(extract_as_is) != str
                    or type(extracted_indicator_types) != list
                ):
                    invalid_incident_fields.append(incident_field)

                # If trying to extract without regex make sure extract all is set to
                # False and the extracted indicators list is empty
                elif extract_as_is != "":
                    if extracting_all is True or len(extracted_indicator_types) > 0:
                        invalid_incident_fields.append(incident_field)

                # If trying to extract with regex make sure extract all is set to
                # False and the extract_as_is should be set to an empty string
                elif len(extracted_indicator_types) > 0:
                    if extracting_all is True or extract_as_is != "":
                        invalid_incident_fields.append(incident_field)

            if invalid_incident_fields:
                (
                    error_message,
                    error_code,
                ) = Errors.incident_type_auto_extract_fields_invalid(
                    invalid_incident_fields
                )
                if self.handle_error(error_message, error_code, self.file_path):
                    is_valid = False

        if auto_extract_mode not in ["All", "Specific"]:
            error_message, error_code = Errors.incident_type_invalid_auto_extract_mode()
            if self.handle_error(error_message, error_code, self.file_path):
                is_valid = False

        return is_valid

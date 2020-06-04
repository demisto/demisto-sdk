import re
from distutils.version import LooseVersion

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator

# Checks if playbookID is a UUID format
INVALID_PLAYBOOK_ID = r'[\w\d]{8}-[\w\d]{4}-[\w\d]{4}-[\w\d]{4}-[\w\d]{12}'


class IncidentTypeValidator(ContentEntityValidator):
    """IncidentTypeValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """

    def is_backward_compatible(self):
        """Check whether the Incident Type is backward compatible or not
        """
        if not self.old_file:
            return True

        is_bc_broke = any(
            [
                self.is_changed_from_version()
            ]
        )

        return not is_bc_broke

    def is_valid_incident_type(self, validate_rn=True):
        """Check whether the Incident Type is valid or not
        """
        is_incident_type__valid = all([
            super().is_valid_file(validate_rn),
            self.is_valid_version()
        ])

        # check only on added files
        if not self.old_file:
            is_incident_type__valid = all([
                is_incident_type__valid,
                self.is_id_equals_name(),
                self.is_including_int_fields(),
                self.is_valid_playbook_id()
            ])

        return is_incident_type__valid

    def is_valid_version(self):
        # type: () -> bool
        """Check if a valid version.
        Returns:
            bool. Whether the version is valid or not.
        """
        return super(IncidentTypeValidator, self)._is_valid_version()

    def is_current_valid_from_version(self):
        # type: () -> bool
        """Check if the current file fromversion is valid.
        Returns:
            bool. Whether the current fromversion is valid or not.
        """
        is_valid = True

        # if not a new file, will be checked here
        # if has an old_file, will be checked in BC checks
        if not self.old_file:
            try:
                from_version = self.current_file.get("fromVersion", "0.0.0")
                if LooseVersion(from_version) < LooseVersion("5.0.0"):
                    error_message, error_code = Errors.incident_field_or_type_from_version_5()
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        is_valid = False
            except (AttributeError, ValueError):
                error_message, error_code = Errors.invalid_incident_field_or_type_from_version()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_valid = False

        return is_valid

    def is_id_equals_name(self):
        # type: () -> bool
        """Check whether the incident Type ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super(IncidentTypeValidator, self)._is_id_equals_name('incident_type')

    def is_changed_from_version(self):
        # type: () -> bool
        """Check if fromversion has been changed.
       Returns:
           bool. Whether fromversion has been changed.
       """
        is_bc_broke = False

        old_from_version = self.old_file.get('fromVersion', None)
        if old_from_version:
            current_from_version = self.current_file.get('fromVersion', None)
            if old_from_version != current_from_version:
                error_message, error_code = Errors.from_version_modified_after_rename()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_bc_broke = True
        return is_bc_broke

    def is_including_int_fields(self):
        # type: () -> bool
        """Check if including required fields, only from 5.0.0.
        Returns:
            bool. Whether the included fields have a positive integer value.
        """
        is_valid = True
        fields_to_include = ['hours', 'days', 'weeks', 'hoursR', 'daysR', 'weeksR']

        try:
            from_version = self.current_file.get("fromVersion", "0.0.0")
            if LooseVersion(from_version) >= LooseVersion("5.0.0"):
                for field in fields_to_include:
                    int_field = self.current_file.get(field, -1)
                    if not isinstance(int_field, int) or int_field < 0:
                        error_message, error_code = Errors.incident_type_integer_field(field)
                        if self.handle_error(error_message, error_code, file_path=self.file_path):
                            is_valid = False

        except (AttributeError, ValueError):
            error_message, error_code = Errors.invalid_incident_field_or_type_from_version()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    def is_valid_playbook_id(self):
        # type: () -> bool
        """Check if playbookId is valid
        Returns:
            bool. True if playbook ID is valid, False otherwise.
        """
        playbook_id = self.current_file.get('playbookId', '')
        if playbook_id and re.search(INVALID_PLAYBOOK_ID, playbook_id):
            error_message, error_code = Errors.incident_type_invalid_playbook_id_field()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

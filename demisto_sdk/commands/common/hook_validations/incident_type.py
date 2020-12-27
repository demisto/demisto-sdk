import re

from demisto_sdk.commands.common.content.objects.pack_objects.incident_type.incident_type import \
    IncidentType
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from packaging.version import Version

# Checks if playbookID is a UUID format
INVALID_PLAYBOOK_ID = r'[\w\d]{8}-[\w\d]{4}-[\w\d]{4}-[\w\d]{4}-[\w\d]{12}'


class IncidentTypeValidator(ContentEntityValidator):
    """IncidentTypeValidator is designed to validate the correctness of the file structure we enter to content repo.
    And also try to catch possible Backward compatibility breaks due to the performed changes.
    """

    def __init__(self, structure_validator, ignored_errors=None, print_as_warnings=False):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
        self.incident_type_object = IncidentType(structure_validator.file_path)

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
            current_from_version = self.incident_type_object.get('fromVersion', None)
            if old_from_version != current_from_version:
                error_message, error_code = Errors.from_version_modified_after_rename()
                if self.handle_error(error_message, error_code, file_path=self.incident_type_object.path):
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
            if self.incident_type_object.from_version >= Version("5.0.0"):
                for field in fields_to_include:
                    int_field = self.current_file.get(field, -1)
                    if not isinstance(int_field, int) or int_field < 0:
                        error_message, error_code = Errors.incident_type_integer_field(field)
                        if self.handle_error(error_message, error_code, file_path=self.incident_type_object.path):
                            is_valid = False

        except (AttributeError, ValueError):
            error_message, error_code = Errors.invalid_incident_field_or_type_from_version()
            if self.handle_error(error_message, error_code, file_path=self.incident_type_object.path):
                is_valid = False

        return is_valid

    def is_valid_playbook_id(self):
        # type: () -> bool
        """Check if playbookId is valid
        Returns:
            bool. True if playbook ID is valid, False otherwise.
        """
        playbook_id = self.incident_type_object.get('playbookId', '')
        if playbook_id and re.search(INVALID_PLAYBOOK_ID, playbook_id):
            error_message, error_code = Errors.incident_type_invalid_playbook_id_field()
            if self.handle_error(error_message, error_code, file_path=self.incident_type_object.path):
                return False
        return True

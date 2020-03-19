from distutils.version import LooseVersion

from demisto_sdk.commands.common.constants import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.tools import print_error


class IncidentTypeValidator(BaseValidator):
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
                self.is_including_fields()
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
                    print_error(f'{self.file_path}: fromVersion must be at least 5.0.0')
                    is_valid = False
            except (AttributeError, ValueError):
                print_error(f'{self.file_path}: "fromVersion" has an invalid value.')
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
                print_error(Errors.from_version_modified_after_rename())
                is_bc_broke = True
        return is_bc_broke

    def is_including_int_fields(self):
        # type: () -> bool
        """Check if including required fields, only from 5.0.0.
        Returns:
            bool. Whether the fields .
        """
        is_valid = True
        fields_to_include = ['hours', 'days', 'weeks', 'hoursR', 'daysR', 'weeksR']

        try:
            from_version = self.current_file.get("fromVersion", "0.0.0")
            if LooseVersion(from_version) >= LooseVersion("5.0.0"):
                for field in fields_to_include:
                    int_field = self.current_file.get(field)
                    if not int_field or not isinstance(int_field, int):
                        is_valid = False
                        print_error(f'{self.file_path}: the field {field} needs to be included as an integer.'
                                    f' Please add it.\n')
        except (AttributeError, ValueError):
            print_error(f'{self.file_path}: "fromVersion" has an invalid value.')
            is_valid = False

        return is_valid

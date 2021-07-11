from distutils.version import LooseVersion

import click
from demisto_sdk.commands.common.constants import \
    LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import \
    get_all_incident_and_indicator_fields_from_id_set
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION = '6.0.0'
VALID_TYPE_INCOMING = 'mapping-incoming'
VALID_TYPE_OUTGOING = 'mapping-outgoing'


class MapperValidator(ContentEntityValidator):
    def __init__(self, structure_validator, ignored_errors=None, print_as_warnings=False, suppress_print=False,
                 json_file_path=None):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.from_version = ''
        self.to_version = ''

    def is_valid_mapper(self, validate_rn=True, id_set_file=None, is_circle=False):
        """Checks whether the mapper is valid or not.

        Returns:
            bool. True if mapper is valid, else False.
        """
        return all([
            super().is_valid_file(validate_rn),
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
            self.is_valid_type(),
            self.is_incident_field_exist(id_set_file, is_circle),
            self.is_id_equals_name(),
        ])

    def is_valid_version(self):
        """Checks if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_backward_compatible(self):
        # type: () -> bool
        """Check whether the Mapper is backward compatible or not, update the _is_valid field to determine that"""

        answers = [
            self.is_field_mapping_removed(),
        ]
        return not any(answers)

    def is_field_mapping_removed(self):
        """checks if some incidents fields or incidents types were removed"""
        old_mapper = self.old_file.get('mapping', {})
        current_mapper = self.current_file.get('mapping', {})

        old_incidents_types = {inc for inc in old_mapper}
        current_incidents_types = {inc for inc in current_mapper}
        if not old_incidents_types.issubset(current_incidents_types):
            removed_incident_types = old_incidents_types - current_incidents_types
            removed_dict = {}
            for removed in removed_incident_types:
                removed_dict[removed] = old_mapper[removed]
            error_message, error_code = Errors.removed_incident_types(removed_dict)
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 warning=self.structure_validator.quite_bc):
                self.is_valid = False
                return True
        else:
            removed_incident_fields = {}
            for inc in old_incidents_types:
                old_incident_fields = old_mapper[inc].get('internalMapping', {})
                current_incident_fields = current_mapper[inc].get('internalMapping', {})
                old_fields = {inc for inc in old_incident_fields}
                current_fields = {inc for inc in current_incident_fields}

                if not old_fields.issubset(current_fields):
                    removed_fields = old_fields - current_fields
                    removed_incident_fields[inc] = removed_fields

            if removed_incident_fields:
                error_message, error_code = Errors.changed_incident_field_in_mapper(removed_incident_fields)
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     warning=self.structure_validator.quite_bc):
                    self.is_valid = False
                    return True

        return False

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.current_file.get('fromVersion', '') or self.current_file.get('fromversion')
        if from_version:
            self.from_version = from_version
            if LooseVersion(from_version) < LooseVersion(FROM_VERSION):
                error_message, error_code = Errors.invalid_from_version_in_mapper()
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     suggested_fix=Errors.suggest_fix(self.file_path)):
                    return False
        else:
            error_message, error_code = Errors.missing_from_version_in_mapper()
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 suggested_fix=Errors.suggest_fix(self.file_path)):
                return False
        return True

    def is_valid_to_version(self):
        """Checks if to version is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        to_version = self.current_file.get('toVersion', '') or self.current_file.get('toversion', '')
        if to_version:
            self.to_version = to_version
            if LooseVersion(to_version) < LooseVersion(FROM_VERSION):
                error_message, error_code = Errors.invalid_to_version_in_mapper()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version and self.from_version:
            if LooseVersion(self.to_version) <= LooseVersion(self.from_version):
                error_message, error_code = Errors.from_version_higher_to_version()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.current_file.get('type') not in [VALID_TYPE_INCOMING, VALID_TYPE_OUTGOING]:
            error_message, error_code = Errors.invalid_type_in_mapper()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_incident_field_exist(self, id_set_file, is_circle) -> bool:
        """Checks if incident field is valid - exist in the content.

        Returns:
            bool. True if incident field is valid, else False.
        """
        if not is_circle:
            return True

        if not id_set_file:
            click.secho("Skipping mapper incident field validation. Could not read id_set.json.", fg="yellow")
            return True

        built_in_fields = [field.lower() for field in BUILT_IN_FIELDS] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS

        content_incident_fields = get_all_incident_and_indicator_fields_from_id_set(id_set_file, 'mapper')

        invalid_inc_fields_list = []
        mapper = self.current_file.get('mapping', {})
        for key, value in mapper.items():
            incident_fields = value.get('internalMapping', {})

            for inc_name, inc_info in incident_fields.items():
                # for incoming mapper
                if self.current_file.get('type', {}) == "mapping-incoming":
                    if inc_name not in content_incident_fields and inc_name.lower() not in built_in_fields:
                        invalid_inc_fields_list.append(inc_name)

                # for outgoing mapper
                if self.current_file.get('type', {}) == "mapping-outgoing":
                    # for inc timer type: "field.StartDate, and for using filters: "simple": "".
                    if inc_info['simple'] not in content_incident_fields and inc_info['simple'] not in built_in_fields \
                            and inc_info['simple'].split('.')[0] not in content_incident_fields and inc_info['simple']:
                        invalid_inc_fields_list.append(inc_name) if inc_info['simple'] else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_mapper(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_id_equals_name(self):
        """Check whether the mapper ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name('mapper')

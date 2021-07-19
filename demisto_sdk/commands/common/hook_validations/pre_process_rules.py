import os
from abc import ABC, abstractmethod
from distutils.version import LooseVersion

import click
from demisto_sdk.commands.common.constants import \
    PRE_PROCESS_RULES_BUILT_IN_FIELDS
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import (get_all_incident_and_indicator_fields_from_id_set)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

# TODO Correct??
FROM_VERSION_PRE_PROCESS_RULES = '6.0.0'


class PreprocessRulesBaseValidator(ContentEntityValidator, ABC):
    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False,
                 json_file_path=None, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings,
                         json_file_path=json_file_path, **kwargs)
        self.from_version = self.current_file.get('fromVersion')
        self.to_version = self.current_file.get('toVersion')

    def is_valid_pre_process_rules(self, validate_rn=True, id_set_file=None, is_circle=False) -> bool:
        """Check whether the pre_process_rules is valid or not.

        Returns:
            bool. Whether the pre_process_rules is valid or not
        """
        # PreProcessRules files have fromServerVersion instead of fromVersion
        return all([
                    # super().is_valid_file(validate_rn),
                    super().is_valid_version(),
                    self.is_valid_version(),
                    self.is_valid_from_version(),
                    self.is_valid_to_version(),
                    self.is_to_version_higher_than_from_version(),
                    self.is_valid_file_path(),
                    self.is_incident_field_exist(id_set_file, is_circle),
                    ])

    def is_valid_version(self) -> bool:
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    # TODO Needed?
    def is_to_version_higher_than_from_version(self) -> bool:
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        # if self.to_version and self.from_version:
        #     if LooseVersion(self.to_version) <= LooseVersion(self.from_version):
        #         error_message, error_code = Errors.from_version_higher_to_version()
        #         if self.handle_error(error_message, error_code, file_path=self.file_path):
        #             return False
        return True

    @abstractmethod
    def is_valid_from_version(self) -> bool:
        pass

    @abstractmethod
    def is_valid_to_version(self) -> bool:
        pass

    @abstractmethod
    def is_valid_file_path(self) -> bool:
        pass

    @abstractmethod
    def is_incident_field_exist(self, id_set_file, is_circle) -> bool:
        pass




class PreProcessRulesValidator(PreprocessRulesBaseValidator):

    # TODO Needed?
    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        # if self.from_version:
        #     if LooseVersion(self.from_version) >= LooseVersion(FROM_VERSION_PRE_PROCESS_RULES):
        #         error_message, error_code = Errors.invalid_version_in_pre_process_rules('fromVersion')
        #         if self.handle_error(error_message, error_code, file_path=self.file_path):
        #             return False
        return True

    # TODO Needed?
    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        # if not self.to_version or LooseVersion(self.to_version) >= LooseVersion(FROM_VERSION_PRE_PROCESS_RULES):
        #     error_message, error_code = Errors.invalid_version_in_pre_process_rules('toVersion')
        #     if self.handle_error(error_message, error_code, file_path=self.file_path):
        #         return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(self.file_path)
        # TODO Is this a good name? Maybe pre_process_rules? See Errors.invalid_file_path_pre_process_rules
        if not output_basename.startswith('preprocessrule-'):
            error_message, error_code = Errors.invalid_file_path_pre_process_rules(output_basename)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    # TODO Needed?
    def is_incident_field_exist(self, id_set_file, is_circle) -> bool:
        # TODO Fix if needed
        """Checks if incident field is valid - exist in the content.

        Returns:
            bool. True if incident field is valid, else False.
        """
        if not is_circle:
            return True

        if not id_set_file:
            click.secho("Skipping mapper incident field validation. Could not read id_set.json.", fg="yellow")
            return True

        pre_process_rules_incident_fields = []

        layout = self.current_file.get('layout', {})
        pre_process_rules_sections = layout.get('sections', [])
        for section in pre_process_rules_sections:
            for field in section.get('fields', []):
                inc_field = field.get('fieldId', '')
                pre_process_rules_incident_fields.append(inc_field.replace('incident_', ''))

        layout_tabs = layout.get('tabs', [])
        for tab in layout_tabs:
            pre_process_rules_sections = tab.get('sections', [])

            for section in pre_process_rules_sections:
                if section and section.get('items'):
                    for item in section.get('items', []):
                        inc_field = item.get('fieldId', '')
                        pre_process_rules_incident_fields.append(inc_field.replace('incident_', '').replace('indicator_', ''))

        content_incident_fields = get_all_incident_and_indicator_fields_from_id_set(id_set_file, 'layout')

        built_in_fields = [field.lower() for field in BUILT_IN_FIELDS] + PRE_PROCESS_RULES_BUILT_IN_FIELDS

        invalid_inc_fields_list = []
        for inc_field in pre_process_rules_incident_fields:
            if inc_field and inc_field.lower() not in built_in_fields and inc_field not in content_incident_fields:
                invalid_inc_fields_list.append(inc_field) if inc_field not in invalid_inc_fields_list else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_pre_process_rules(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

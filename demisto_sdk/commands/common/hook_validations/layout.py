import os
from abc import ABC, abstractmethod
from distutils.version import LooseVersion

import click
from demisto_sdk.commands.common.constants import \
    LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import (
    LAYOUT_CONTAINER_FIELDS, get_all_incident_and_indicator_fields_from_id_set)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION_LAYOUTS_CONTAINER = '6.0.0'


class LayoutBaseValidator(ContentEntityValidator, ABC):
    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False,
                 json_file_path=None, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings,
                         json_file_path=json_file_path, **kwargs)
        self.from_version = self.current_file.get('fromVersion')
        self.to_version = self.current_file.get('toVersion')

    def is_valid_layout(self, validate_rn=True, id_set_file=None, is_circle=False) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return all([super().is_valid_file(validate_rn),
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

    def is_to_version_higher_than_from_version(self) -> bool:
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


class LayoutsContainerValidator(LayoutBaseValidator):
    def is_valid_layout(self, validate_rn=True, id_set_file=None, is_circle=False) -> bool:
        return all([super().is_valid_layout(),
                    self.is_id_equals_name()
                    ])

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if LooseVersion(self.from_version) < LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('fromVersion')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if self.to_version and LooseVersion(self.to_version) < LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('toVersion')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(self.file_path)
        if not output_basename.startswith('layoutscontainer-'):
            error_message, error_code = Errors.invalid_file_path_layoutscontainer(output_basename)
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

        layout_container_items = []
        for layout_container_field in LAYOUT_CONTAINER_FIELDS:
            if self.current_file.get(layout_container_field):
                layout_container_items.append(layout_container_field)

        layout_incident_fields = []
        for layout_container_item in layout_container_items:
            layout = self.current_file.get(layout_container_item, {})
            layout_tabs = layout.get('tabs', [])

            for layout_tab in layout_tabs:
                layout_sections = layout_tab.get('sections', [])

                for section in layout_sections:
                    if section and section.get('items'):
                        for item in section.get('items', []):
                            layout_incident_fields.append(item.get('fieldId', '').replace('incident_', ''))

        content_incident_fields = get_all_incident_and_indicator_fields_from_id_set(id_set_file, 'layout')

        built_in_fields = [field.lower() for field in BUILT_IN_FIELDS] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS

        invalid_inc_fields_list = []
        for inc_field in layout_incident_fields:
            if inc_field and inc_field.lower() not in built_in_fields and inc_field not in content_incident_fields:
                invalid_inc_fields_list.append(inc_field) if inc_field not in invalid_inc_fields_list else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_layout(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_id_equals_name(self):
        """Check whether the playbook ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name('layoutscontainer')


class LayoutValidator(LayoutBaseValidator):

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.from_version:
            if LooseVersion(self.from_version) >= LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
                error_message, error_code = Errors.invalid_version_in_layout('fromVersion')
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if not self.to_version or LooseVersion(self.to_version) >= LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layout('toVersion')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(self.file_path)
        if not output_basename.startswith('layout-'):
            error_message, error_code = Errors.invalid_file_path_layout(output_basename)
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

        layout_incident_fields = []

        layout = self.current_file.get('layout', {})
        layout_sections = layout.get('sections', [])
        for section in layout_sections:
            for field in section.get('fields', []):
                inc_field = field.get('fieldId', '')
                layout_incident_fields.append(inc_field.replace('incident_', ''))

        layout_tabs = layout.get('tabs', [])
        for tab in layout_tabs:
            layout_sections = tab.get('sections', [])

            for section in layout_sections:
                if section and section.get('items'):
                    for item in section.get('items', []):
                        inc_field = item.get('fieldId', '')
                        layout_incident_fields.append(inc_field.replace('incident_', '').replace('indicator_', ''))

        content_incident_fields = get_all_incident_and_indicator_fields_from_id_set(id_set_file, 'layout')

        built_in_fields = [field.lower() for field in BUILT_IN_FIELDS] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS

        invalid_inc_fields_list = []
        for inc_field in layout_incident_fields:
            if inc_field and inc_field.lower() not in built_in_fields and inc_field not in content_incident_fields:
                invalid_inc_fields_list.append(inc_field) if inc_field not in invalid_inc_fields_list else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_layout(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

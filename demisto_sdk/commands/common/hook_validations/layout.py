import os
from abc import ABC, abstractmethod
from distutils.version import LooseVersion
from typing import Dict, List

import click

from demisto_sdk.commands.common.constants import (DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION,
                                                   LAYOUT_AND_MAPPER_BUILT_IN_FIELDS,
                                                   LAYOUTS_CONTAINERS_OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import ContentEntityValidator
from demisto_sdk.commands.common.tools import (LAYOUT_CONTAINER_FIELDS,
                                               get_all_incident_and_indicator_fields_from_id_set,
                                               get_invalid_incident_fields_from_layout)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION_LAYOUTS_CONTAINER = '6.0.0'


class LayoutBaseValidator(ContentEntityValidator, ABC):
    def __init__(self, structure_validator, ignored_errors=False, print_as_warnings=False,
                 json_file_path=None, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings,
                         json_file_path=json_file_path, **kwargs)
        self.from_version = self.current_file.get('fromVersion', DEFAULT_CONTENT_ITEM_FROM_VERSION)
        self.to_version = self.current_file.get('toVersion', DEFAULT_CONTENT_ITEM_TO_VERSION)

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

    @error_codes('CL106')
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

    @staticmethod
    def get_invalid_incident_fields_from_tabs(layout_tabs, content_fields) -> List[str]:
        """
        Get the invalid incident fields from layout tabs.

        Args:
            layout_tabs (list): a list of the layout tabs.
            content_fields (list): a list of the content field items.

        Returns:
            list[str]: incident fields which do not exist in the content items.
        """
        non_existent_incident_fields = []

        for tab in layout_tabs:
            layout_sections = tab.get('sections', [])
            for section in layout_sections:
                items = section.get('items', [])
                non_existent_incident_fields.extend(
                    get_invalid_incident_fields_from_layout(layout_incident_fields=items, content_fields=content_fields)
                )

        return non_existent_incident_fields

    @staticmethod
    def get_fields_from_id_set(id_set_file: Dict[str, List]) -> List[str]:
        """
        Get all the available layout fields from the id set.

        Args:
            id_set_file (dict): content of the id set file.

        Returns:
            list[str]: available indicator/incident fields from the id set file.
        """
        return get_all_incident_and_indicator_fields_from_id_set(id_set_file, 'layout') + [
            field.lower() for field in BUILT_IN_FIELDS
        ] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS

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
    def __init__(self, structure_validator, **kwargs):
        super().__init__(structure_validator, oldest_supported_version=LAYOUTS_CONTAINERS_OLDEST_SUPPORTED_VERSION, **kwargs)

    def is_valid_layout(self, validate_rn=True, id_set_file=None, is_circle=False) -> bool:
        return all([super().is_valid_layout(),
                    self.is_id_equals_name(),
                    ])

    @error_codes('LO101')
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

    @error_codes('LO101')
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

    @error_codes('LO103')
    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(self.file_path)
        if not output_basename.startswith('layoutscontainer-'):
            error_message, error_code = Errors.invalid_file_path_layoutscontainer(output_basename)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes('LO104')
    def is_incident_field_exist(self, id_set_file: Dict[str, List], is_circle: bool) -> bool:
        """
        Check if the incident fields which are part of the layout actually exist in the content items (id set).

        Args:
            id_set_file (dict): content of the id set file.
            is_circle (bool): whether running on circle CI or not, True if yes, False if not.

        Returns:
            bool: False if there are incident fields which are part of the layout that do not exist in content items.
                True if there aren't.
        """
        if not is_circle:
            return True

        if not id_set_file:
            click.secho("Skipping mapper incident field validation. Could not read id_set.json.", fg="yellow")
            return True

        content_fields = self.get_fields_from_id_set(id_set_file=id_set_file)
        invalid_incident_fields = []

        layout_container_items = [
            layout_container_field for layout_container_field
            in LAYOUT_CONTAINER_FIELDS if self.current_file.get(layout_container_field)
        ]

        for layout_container_item in layout_container_items:
            layout = self.current_file.get(layout_container_item, {})
            layout_tabs = layout.get('tabs', [])
            invalid_incident_fields.extend(
                self.get_invalid_incident_fields_from_tabs(layout_tabs=layout_tabs, content_fields=content_fields)
            )

        if invalid_incident_fields:
            error_message, error_code = Errors.invalid_incident_field_in_layout(invalid_incident_fields)
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

    @error_codes('LO100')
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

    @error_codes('LO100')
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

    @error_codes('LO102')
    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(self.file_path)
        if not output_basename.startswith('layout-'):
            error_message, error_code = Errors.invalid_file_path_layout(output_basename)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes('LO104')
    def is_incident_field_exist(self, id_set_file: Dict[str, List], is_circle: bool) -> bool:
        """
        Check if the incident fields which are part of the layout actually exist in the content items (id set).

        Args:
            id_set_file (dict): content of the id set file.
            is_circle (bool): whether running on circle CI or not, True if yes, False if not.

        Returns:
            bool: False if there are incident fields which are part of the layout that do not exist in content items.
                True if there aren't.
        """
        if not is_circle:
            return True

        if not id_set_file:
            click.secho("Skipping mapper incident field validation. Could not read id_set.json.", fg="yellow")
            return True

        invalid_incident_fields = []
        content_fields = self.get_fields_from_id_set(id_set_file=id_set_file)

        layout = self.current_file.get('layout', {})
        layout_sections = layout.get('sections', [])
        for section in layout_sections:
            fields = section.get('fields', [])
            invalid_incident_fields.extend(
                get_invalid_incident_fields_from_layout(layout_incident_fields=fields, content_fields=content_fields)
            )

        layout_tabs = layout.get('tabs', [])
        invalid_incident_fields.extend(
            self.get_invalid_incident_fields_from_tabs(layout_tabs=layout_tabs, content_fields=content_fields)
        )

        if invalid_incident_fields:
            error_message, error_code = Errors.invalid_incident_field_in_layout(invalid_incident_fields)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

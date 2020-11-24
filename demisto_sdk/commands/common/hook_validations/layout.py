import os
from abc import ABC, abstractmethod
from distutils.version import LooseVersion

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.id import IDSetValidator
from demisto_sdk.commands.create_id_set.create_id_set import IDSetCreator
from demisto_sdk.commands.common.tools import open_id_set_file, LAYOUT_CONTAINER_FIELDS
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS
from demisto_sdk.commands.common.constants import LAYOUT_BUILT_IN_FIELDS

FROM_VERSION_LAYOUTS_CONTAINER = '6.0.0'


class LayoutBaseValidator(ContentEntityValidator, ABC):
    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, **kwargs)
        self.from_version = self.current_file.get('fromVersion')
        self.to_version = self.current_file.get('toVersion')

    def is_valid_layout(self, validate_rn=True) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return all([super().is_valid_file(validate_rn),
                    self.is_valid_version(),
                    self.is_valid_from_version(),
                    self.is_valid_to_version(),
                    self.is_to_version_higher_than_from_version(),
                    self.is_valid_file_path()
                    # self.is_valid_incident_field()
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
    def is_valid_incident_field(self) -> bool:
        pass


class LayoutsContainerValidator(LayoutBaseValidator):
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

    def is_valid_incident_field(self) -> bool:
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
                            layout_incident_fields.append(item.get('fieldId', ''))

        id_set_path = IDSetValidator.ID_SET_PATH
        id_set = open_id_set_file(id_set_path)
        if not id_set_path or not os.path.isfile(id_set_path):
            id_set = IDSetCreator(print_logs=False).create_id_set()

        content_incident_fields = []
        content_all_incident_fields = id_set.get('IncidentFields')
        for content_inc_field in content_all_incident_fields:
            for inc_name, inc_field in content_inc_field.items():
                content_incident_fields.append(inc_name.replace('incident_', ''))

        content_indicator_fields = []
        content_all_indicator_fields = id_set.get('IndicatorFields')
        for content_ind_field in content_all_indicator_fields:
            for ind_name, ind_field in content_ind_field.items():
                content_indicator_fields.append(ind_name.replace('indicator_', ''))

        built_in_fields_layout = [field.lower() for field in BUILT_IN_FIELDS]
        all_fields_in_content = \
            content_incident_fields + content_indicator_fields + LAYOUT_BUILT_IN_FIELDS + built_in_fields_layout

        invalid_inc_fields_list = []
        for layout_inc_field in layout_incident_fields:
            if layout_inc_field and layout_inc_field not in all_fields_in_content:
                invalid_inc_fields_list.append(layout_inc_field) if layout_inc_field not in invalid_inc_fields_list \
                    else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_layout(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True


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

    def is_valid_incident_field(self) -> bool:
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

        id_set_path = IDSetValidator.ID_SET_PATH
        id_set = open_id_set_file(id_set_path)
        if not id_set_path or not os.path.isfile(id_set_path):
            id_set = IDSetCreator(print_logs=False).create_id_set()

        content_incident_fields = []
        content_all_incident_fields = id_set.get('IncidentFields')
        for content_inc_field in content_all_incident_fields:
            for inc_name, inc_field in content_inc_field.items():
                content_incident_fields.append(inc_name.replace('incident_', ''))

        content_indicator_fields = []
        content_all_indicator_fields = id_set.get('IndicatorFields')
        for content_ind_field in content_all_indicator_fields:
            for ind_name, ind_field in content_ind_field.items():
                content_indicator_fields.append(ind_name.replace('indicator_', ''))

        built_in_fields_layout = [field.lower() for field in BUILT_IN_FIELDS]
        all_fields_in_content = \
            content_incident_fields + content_indicator_fields + LAYOUT_BUILT_IN_FIELDS + built_in_fields_layout

        invalid_inc_fields_list = []
        for layout_inc_field in layout_incident_fields:
            if layout_inc_field and layout_inc_field not in all_fields_in_content:
                invalid_inc_fields_list.append(layout_inc_field) if layout_inc_field not in invalid_inc_fields_list \
                    else None

        if invalid_inc_fields_list:
            error_message, error_code = Errors.invalid_incident_field_in_layout(invalid_inc_fields_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True


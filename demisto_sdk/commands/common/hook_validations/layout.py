from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    LAYOUT_AND_MAPPER_BUILT_IN_FIELDS,
    LAYOUTS_CONTAINERS_OLDEST_SUPPORTED_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    LAYOUT_CONTAINER_FIELDS,
    get_all_incident_and_indicator_fields_from_id_set,
    get_invalid_incident_fields_from_layout,
    get_item_marketplaces,
)
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

FROM_VERSION_LAYOUTS_CONTAINER = "6.0.0"


class LayoutBaseValidator(ContentEntityValidator, ABC):
    def __init__(
        self, structure_validator, ignored_errors=False, json_file_path=None, **kwargs
    ):
        super().__init__(
            structure_validator, ignored_errors, json_file_path=json_file_path, **kwargs
        )
        self.from_version = self.current_file.get(
            "fromVersion", DEFAULT_CONTENT_ITEM_FROM_VERSION
        )
        self.to_version = self.current_file.get(
            "toVersion", DEFAULT_CONTENT_ITEM_TO_VERSION
        )

    def is_valid_layout(
        self, validate_rn=True, id_set_file=None, is_circle=False
    ) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return all(
            [
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_valid_from_version(),
                self.is_valid_to_version(),
                self.is_to_version_higher_than_from_version(),
                self.is_valid_file_path(),
                self.is_incident_field_exist(id_set_file, is_circle),
            ]
        )

    def is_valid_version(self) -> bool:
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    @error_codes("CL106")
    def is_to_version_higher_than_from_version(self) -> bool:
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
            layout_sections = tab.get("sections", [])
            for section in layout_sections:
                items = section.get("items", [])
                non_existent_incident_fields.extend(
                    get_invalid_incident_fields_from_layout(
                        layout_incident_fields=items, content_fields=content_fields
                    )
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
        return (
            get_all_incident_and_indicator_fields_from_id_set(id_set_file, "layout")
            + [field.lower() for field in BUILT_IN_FIELDS]
            + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
        )

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
        super().__init__(
            structure_validator,
            oldest_supported_version=LAYOUTS_CONTAINERS_OLDEST_SUPPORTED_VERSION,
            **kwargs,
        )

    def is_valid_layout(
        self, validate_rn=True, id_set_file=None, is_circle=False
    ) -> bool:
        return all(
            [
                super().is_valid_layout(
                    validate_rn=validate_rn,
                    id_set_file=id_set_file,
                    is_circle=is_circle,
                ),
                self.is_id_equals_name(),
                self.is_valid_mpv2_layout(),
            ]
        )

    @error_codes("LO101")
    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if Version(self.from_version) < Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer(
                "fromVersion"
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("LO101")
    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if self.to_version and Version(self.to_version) < Version(
            FROM_VERSION_LAYOUTS_CONTAINER
        ):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer(
                "toVersion"
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("LO103")
    def is_valid_file_path(self) -> bool:
        output_basename = Path(self.file_path).name
        if not output_basename.startswith("layoutscontainer-"):
            error_message, error_code = Errors.invalid_file_path_layoutscontainer(
                output_basename
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("LO104")
    def is_incident_field_exist(
        self, id_set_file: Dict[str, List], is_circle: bool
    ) -> bool:
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
            logger.info(
                "<yellow>Skipping mapper incident field validation. Could not read id_set.json.</yellow>"
            )
            return True

        content_fields = self.get_fields_from_id_set(id_set_file=id_set_file)
        invalid_incident_fields = []

        layout_container_items = [
            layout_container_field
            for layout_container_field in LAYOUT_CONTAINER_FIELDS
            if self.current_file.get(layout_container_field)
        ]

        for layout_container_item in layout_container_items:
            layout = self.current_file.get(layout_container_item, {})
            layout_tabs = layout.get("tabs", [])
            invalid_incident_fields.extend(
                self.get_invalid_incident_fields_from_tabs(
                    layout_tabs=layout_tabs, content_fields=content_fields
                )
            )

        if invalid_incident_fields:
            error_message, error_code = Errors.invalid_incident_field_in_layout(
                invalid_incident_fields
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_id_equals_name(self):
        """Check whether the playbook ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super()._is_id_equals_name("layoutscontainer")

    @error_codes("LO107")
    def is_valid_mpv2_layout(self):
        invalid_sections = [
            "evidence",
            "childInv",
            "linkedIncidents",
            "team",
            "droppedIncidents",
            "todoTasks",
        ]
        invalid_tabs = ["canvas", "evidenceBoard", "relatedIncidents"]
        invalid_types_contained = []

        marketplace_versions = get_item_marketplaces(
            self.file_path, item_data=self.current_file
        )
        if MarketplaceVersions.MarketplaceV2.value not in marketplace_versions:
            return True

        for key, val in self.current_file.items():
            if isinstance(val, dict):
                for tab in val.get("tabs", []) or []:
                    if "type" in tab.keys() and tab.get("type") in invalid_tabs:
                        invalid_types_contained.append(tab.get("type"))
                    sections = tab.get("sections", [])
                    for section in sections:
                        if (
                            "type" in section.keys()
                            and section.get("type") in invalid_sections
                        ):
                            invalid_types_contained.append(section.get("type"))

        if invalid_types_contained:
            error_message, error_code = Errors.layout_container_contains_invalid_types(
                invalid_types_contained
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True


class LayoutValidator(LayoutBaseValidator):
    @error_codes("LO100")
    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.from_version:
            if Version(self.from_version) >= Version(FROM_VERSION_LAYOUTS_CONTAINER):
                error_message, error_code = Errors.invalid_version_in_layout(
                    "fromVersion"
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False
        return True

    @error_codes("LO100")
    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if not self.to_version or Version(self.to_version) >= Version(
            FROM_VERSION_LAYOUTS_CONTAINER
        ):
            error_message, error_code = Errors.invalid_version_in_layout("toVersion")
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("LO102")
    def is_valid_file_path(self) -> bool:
        output_basename = Path(self.file_path).name
        if not output_basename.startswith("layout-"):
            error_message, error_code = Errors.invalid_file_path_layout(output_basename)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("LO104")
    def is_incident_field_exist(
        self, id_set_file: Dict[str, List], is_circle: bool
    ) -> bool:
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
            logger.info(
                "<yellow>Skipping mapper incident field validation. Could not read id_set.json.</yellow>"
            )
            return True

        invalid_incident_fields = []
        content_fields = self.get_fields_from_id_set(id_set_file=id_set_file)

        layout = self.current_file.get("layout", {})
        layout_sections = layout.get("sections", [])
        for section in layout_sections:
            fields = section.get("fields", [])
            invalid_incident_fields.extend(
                get_invalid_incident_fields_from_layout(
                    layout_incident_fields=fields, content_fields=content_fields
                )
            )

        layout_tabs = layout.get("tabs", [])
        invalid_incident_fields.extend(
            self.get_invalid_incident_fields_from_tabs(
                layout_tabs=layout_tabs, content_fields=content_fields
            )
        )

        if invalid_incident_fields:
            error_message, error_code = Errors.invalid_incident_field_in_layout(
                invalid_incident_fields
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

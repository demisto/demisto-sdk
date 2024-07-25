from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Mapper


class IsChangedIncidentTypesAndFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "BC113"
    description = "Validate that no incident types were removed and no incident fields were changed."
    rationale = "We want to ensure no breaking changes are made to existing mappers so customers won't lose data between pack updates."
    error_message = "The Mapper contains modified / removed keys:{0}"
    related_field = "mapping"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        for content_item in content_items:
            (
                removed_incident_types,
                intersected_incident_types,
            ) = self.get_sorted_incident_types(
                content_item.mapping,  # type: ignore[union-attr]
                content_item.old_base_content_object.mapping,  # type: ignore[union-attr]
            )
            removed_incident_field_by_incident_type = (
                self.get_removed_incident_fields_by_incident_type(
                    content_item.mapping,
                    content_item.old_base_content_object.mapping,  # type: ignore[union-attr]
                    intersected_incident_types,
                )
            )
            if error_msg := self.obtain_error_msg(
                removed_incident_types, removed_incident_field_by_incident_type
            ):
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(error_msg),
                        content_object=content_item,
                    )
                )
        return validation_results

    def obtain_error_msg(
        self,
        removed_incident_types: Set[str],
        removed_incident_field_by_incident_type: Dict[str, Set],
    ) -> str:
        """Create a formatted error message from the removed_incident_types and removed_incident_field_by_incident_type.

        Args:
            removed_incident_types (Set[str]): The set of removed incident types.
            removed_incident_field_by_incident_type (Dict[str, Set]): The mapping between each incident type to the incident fields removed from that type.

        Returns:
            str: The formatted error message.
        """
        error_msg = ""
        if removed_incident_types:
            error_msg += f"\n- The following incident types were removed: {', '.join(removed_incident_types)}."
        if removed_incident_field_by_incident_type:
            error_msg += "\n- The following incident fields were removed from the following incident types:"
            for (
                incident_type,
                missing_incident_fields,
            ) in removed_incident_field_by_incident_type.items():
                error_msg += f"\n\t- The following incident fields were removed from the incident types '{incident_type}': {', '.join(missing_incident_fields)}."
        return error_msg

    def get_removed_incident_fields_by_incident_type(
        self,
        content_item_mappings: Dict[str, Any],
        old_content_item_mappings: Dict[str, Any],
        intersected_incident_types: Set[str],
    ) -> Dict[str, Set[str]]:
        """Retrieve the incident fields removed from each incident type

        Args:
            content_item_mappings (Dict[str, Any]): The content item mapping field.
            old_content_item_mappings (Dict[str, Any]): The old content item mapping field.
            intersected_incident_types (Set[str]): The set of types appears in both content_item_mappings and old_content_item_mappings.

        Returns:
            Dict[str, Set[str]]: The mapping between each incident type to the incident fields removed from that type.
        """
        missing_incident_fields_by_incident_type = {}
        for intersected_incident_type in intersected_incident_types:
            current_incident_field_for_incident_type = {
                inc
                for inc in content_item_mappings[intersected_incident_type].get(
                    "internalMapping", {}
                )
            }
            old_incident_field_for_incident_type = {
                inc
                for inc in old_content_item_mappings[intersected_incident_type].get(
                    "internalMapping", {}
                )
            }
            if (
                removed_fields := old_incident_field_for_incident_type
                - current_incident_field_for_incident_type
            ):
                missing_incident_fields_by_incident_type[intersected_incident_type] = (
                    removed_fields
                )
        return missing_incident_fields_by_incident_type

    def get_sorted_incident_types(
        self,
        content_item_mappings: Dict[str, Any],
        old_content_item_mappings: Dict[str, Any],
    ) -> Tuple[Set[str], Set[str]]:
        """Return the set of removed incident types and the types that match between both mappers.

        Args:
            content_item_mappings (Dict[str, Any]): The content item mapping field.
            old_content_item_mappings (Dict[str, Any]): The old content item mapping field.

        Returns:
            Tuple[Set[str], Set[str]]: The set of removed incident types and the set of types that match between both mappers.
        """
        old_incidents_types = {inc for inc in old_content_item_mappings}
        current_incidents_types = {inc for inc in content_item_mappings}
        return (
            old_incidents_types - current_incidents_types,
            old_incidents_types.intersection(current_incidents_types),
        )

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses, IncidentFieldType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = IncidentField

class SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator(
    BaseValidator[ContentTypes]
):
    error_code = "IF119"
    description = "We do not allow for incidentFields with singleSelect types to have in the selectValues more than one or only emtpy option"
    rationale = "Due to UI issues, we cannot allow more than one or only empty values for selectValues field"
    error_message = "singleSelect type cannot contain"
    fix_message = "Removed all redundant empty values in the selectValues field."
    related_field = "singleSelect, selectValues"
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def select_values_contain_multiple_or_only_empty_values_in_single_select_types(
        self, content_item: ContentTypes,
    ) -> bool:
        if content_item.field_type == IncidentFieldType.SINGLE_SELECT:
            select_values = content_item.select_values or []
            empty_string_count = sum(select_value == "" for select_value in select_values)
            if empty_string_count == 0 or (empty_string_count == 1 and len(select_values) > 1):
                return False
            if empty_string_count == 1:
                self.error_message += " only empty values in the selectValues field."
            if empty_string_count > 1:
                self.error_message += " more than one empty values in the selectValues field."
            return True

        return False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                self.select_values_contain_multiple_or_only_empty_values_in_single_select_types(
                    content_item
                )
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        select_values = content_item.data.get("selectValues") or []

        if all(select_value == "" for select_value in select_values):
            raise Exception

        new_select_values = list(
            filter(lambda select_value: select_value != "", select_values)
        )  # First remove all empty values
        new_select_values.append("")  # Add back one empty value.
        content_item.data["selectValues"] = new_select_values

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )

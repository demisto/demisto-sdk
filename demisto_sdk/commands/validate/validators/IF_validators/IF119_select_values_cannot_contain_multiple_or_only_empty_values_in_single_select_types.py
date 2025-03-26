from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import IncidentFieldType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = IncidentField


def select_values_contain_multiple_or_only_empty_values_in_single_select_types(
    content_item: ContentTypes,
) -> str:
    if content_item.field_type == IncidentFieldType.SINGLE_SELECT:
        select_values = content_item.select_values or []
        empty_string_count = sum(select_value == "" for select_value in select_values)

        if empty_string_count == 0 or (
            empty_string_count == 1 and len(select_values) > 1
        ):
            return ""

        if empty_string_count == 1:
            return "singleSelect types cannot contain only empty values in the selectValues field."
        if empty_string_count > 1:
            return "singleSelect types cannot contain more than one empty values in the selectValues field."

    return ""


class SelectValuesCannotContainMultipleOrOnlyEmptyValuesInSingleSelectTypesValidator(
    BaseValidator[ContentTypes]
):
    error_code = "IF119"
    description = "Ensure incidentFields singleSelect field does not contain more than empty option"
    rationale = "Due to UI issues, we cannot allow more than one or only empty values for selectValues field"
    fix_message = "Removed all redundant empty values in the selectValues field."
    related_field = "singleSelect, selectValues"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []

        for content_item in content_items:
            error_message = select_values_contain_multiple_or_only_empty_values_in_single_select_types(
                content_item
            )

            if error_message:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=error_message,
                        content_object=content_item,
                    )
                )

        return validation_results

    def fix(self, content_item: ContentTypes) -> FixResult:
        select_values = content_item.select_values or []

        if all(select_value == "" for select_value in select_values):
            raise Exception

        new_select_values = list(
            filter(lambda select_value: select_value != "", select_values)
        )  # First remove all empty values
        new_select_values.append("")  # Add back one empty value.
        content_item.data["selectValues"] = content_item.select_values = (
            new_select_values
        )

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )

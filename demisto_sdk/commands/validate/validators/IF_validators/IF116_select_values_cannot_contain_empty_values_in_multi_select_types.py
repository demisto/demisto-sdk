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


def select_values_do_not_contain_empty_values_in_multi_select_types(
    content_item: ContentTypes,
) -> bool:
    if content_item.data.get("type") == IncidentFieldType.MULTI_SELECT:
        select_values = content_item.data.get("selectValues") or []
        if "" in select_values:
            return False
    return True


class SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator(
    BaseValidator[ContentTypes]
):
    error_code = "IF116"
    description = "We do not allow for incidentFields with multySelect types to have in the selectValues emtpy options"
    rationale = "Due to UI issues, we cannot allow empty values for selectValues field"
    error_message = (
        "multiSelect types cannot contain empty values in the selectValues field."
    )
    fix_message = "Removed all empty values in the selectValues field."
    related_field = "multiSelect, selectValues"
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                not select_values_do_not_contain_empty_values_in_multi_select_types(
                    content_item
                )
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        select_values = content_item.data.get("selectValues") or []

        if all(select_value == "" for select_value in select_values):
            raise Exception

        content_item.data["selectValues"] = list(
            filter(lambda select_value: select_value != "", select_values)
        )

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = IncidentField


def select_values_do_not_contain_empty_values_in_multi_select_types(content_item: ContentTypes) -> bool:
    if content_item.data.get("type") == "multiSelect":
        select_values = content_item.data.get("selectValues") or []
        if "" in select_values:
            return False
    return True


class SelectValuesCannotContainEmptyValuesInMultiSelectTypesValidator(BaseValidator[ContentTypes]):
    error_code = "IF116"
    description = ""
    rationale = ""
    error_message = ""
    related_field = ""
    is_auto_fixable = False
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
                select_values_do_not_contain_empty_values_in_multi_select_types(content_item)
            )
        ]
    

    

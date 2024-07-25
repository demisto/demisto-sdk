from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects import (
    GenericType,
    IncidentField,
    IncidentType,
    IndicatorField,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    Integration, Script, IncidentField, IndicatorField, IncidentType, GenericType
]


class SchemaValidator(BaseValidator[ContentTypes]):
    error_code = "ST110"
    description = "Validate that the scheme's structure is valid."
    rationale = "Maintain valid structure for content items."

    # expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message="\n".join(
                    f"problematic field: {error.field_name} | error message: {error.error_message} |"
                    f" error type : {error.error_type}"
                    for error in (
                        content_item.structure_errors or ()
                    )  # TODO remove the 'or' when done with ST
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_invalid_schema(content_item)
        ]

    def is_invalid_schema(self, content_item) -> bool:
        return bool(content_item.structure_errors)

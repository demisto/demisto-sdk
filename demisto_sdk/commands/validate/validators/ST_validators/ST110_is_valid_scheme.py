from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class SchemaValidator(BaseValidator[ContentTypes]):
    error_code = "ST110"
    description = (
        "Validate that the scheme's structure is valid."
    )
    error_message = "Field can't contain None, must be valuable."

    # expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(
            self,
            content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type,
                    content_item.subtype,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_invalid_schema(content_item)
        ]

    def is_invalid_schema(self, content_item) -> bool:
        return bool(content_item.structure_errors)

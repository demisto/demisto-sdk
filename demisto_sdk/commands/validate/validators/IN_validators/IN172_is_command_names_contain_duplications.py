from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsCommandNamesContainDuplicationsValidator(BaseValidator[ContentTypes]):
    error_code = "IN172"
    description = "Prevent duplicate command names in integrations."
    rationale = (
        "The server rejects installing an integration with duplicated command names."
    )
    error_message = "Duplicated command names found: {0}. Each command name must be unique within the integration."
    related_field = "script.commands"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(sorted(duplicates))),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                duplicates := [
                    name
                    for name, count in Counter(
                        command.name for command in content_item.commands
                    ).items()
                    if count > 1
                ]
            )
        ]

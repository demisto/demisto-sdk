from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsQuickactionSupported(BaseValidator[ContentTypes]):
    error_code = "ST112"
    description = "a content item with a quick action command also have supportsquickaction field in top level yml."
    rationale = "Maintain valid structure for content items."
    error_message = (
        "The following commands are using quickaction without the integrations support: {0}. "
        "Remove quickaction or add supportsquickactions: true at the top level yml."
    )
    related_field = "quickaction"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.SCHEMA]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(quickaction_commands)),
                content_object=content_item,
            )
            for content_item in content_items
            if (quickaction_commands := self.is_quickaction_supported(content_item))
        ]

    def is_quickaction_supported(self, content_item):
        if not content_item.supports_quick_actions:
            commands = content_item.commands
            quickaction_commands = []
            for command in commands:
                if command.quickaction:
                    quickaction_commands.append(command.name)

            return quickaction_commands

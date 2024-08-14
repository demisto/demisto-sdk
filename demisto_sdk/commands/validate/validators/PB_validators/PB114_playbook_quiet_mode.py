from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class PlaybookQuietModeValidator(BaseValidator[ContentTypes]):
    error_code = "PB114"
    description = "Validates that playbooks for indicator types will be on quiet mode."
    rationale = (
        "Playbooks for indicators will likely be executing on thousands of indicators "
        "so they need to be on quiet mode."
    )
    error_message = (
        "Playbooks with a playbookInputQuery for indicators should be on quiet mode."
    )
    fix_message = "This playbooks quiet mode was set to true."
    related_field = "quiet"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                any(
                    (i.get("playbookInputQuery") or {}).get("queryEntity")
                    == "indicators"
                    for i in content_item.data.get("inputs", {})
                )
                and not content_item.quiet
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.quiet = True
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )

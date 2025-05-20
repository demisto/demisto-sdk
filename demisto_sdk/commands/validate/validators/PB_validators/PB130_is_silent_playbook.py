from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsSilentPlaybookValidator(BaseValidator[ContentTypes]):
    error_code = "PB130"
    description = "Validate that the 'name', 'ID', and file name of a silent playbook contain the 'silent-' prefix and include the field issilent: true."
    rationale = "A silent playbook must have the 'silent-' prefix in its name, ID, and file name, and the field issilent: true."
    error_message = "Silent playbooks must have 'silent-' as a prefix in the name, ID, and file name, and include the field issilent: true. One or more of these is missing."
    related_field = ""
    is_auto_fixable = False

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
            if is_invalid_silent(content_item)
        ]


def is_invalid_silent(content_item: ContentTypes) -> bool:
    return any(
        [
            content_item.is_silent,
            content_item.data.get("name", "").startswith("silent-"),
            content_item.data.get("id", "").startswith("silent-"),
            content_item.path.name.startswith("silent-"),
        ]
    ) and not all(
        [
            content_item.is_silent,
            content_item.data.get("name", "").startswith("silent-"),
            content_item.data.get("id", "").startswith("silent-"),
            content_item.path.name.startswith("silent-"),
        ]
    )

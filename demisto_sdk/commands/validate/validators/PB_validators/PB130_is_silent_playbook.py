from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook, Trigger]


class IsSilentPlaybookValidator(BaseValidator[ContentTypes]):
    error_code = "PB130"
    description = "Validate that the name and ID of a silent-Playbook contain the silent prefix and include the field issilent: true"
    rationale = "In silent-Playbook the name and ID prefix should be silent and also include the field issilent: true"
    error_message = "Silent-Playbook should have silent as a prefix in the name and ID, as well as the field issilent: true, one of them is missing."
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
    silent_keys = {
        ContentType.PLAYBOOK: ["name", "id"],
        ContentType.TRIGGER: ["trigger_name"]
    }

    keys = silent_keys.get(content_item.content_type, [])

    def check_silent():
        return any([
            content_item.is_silent,
            any(content_item.data.get(key, "").startswith("silent-") for key in keys),
            content_item.path.name.startswith("silent-")
        ]) and not all([
            content_item.is_silent,
            all(content_item.data.get(key, "").startswith("silent-") for key in keys),
            content_item.path.name.startswith("silent-")
        ])

    return check_silent() if keys else True
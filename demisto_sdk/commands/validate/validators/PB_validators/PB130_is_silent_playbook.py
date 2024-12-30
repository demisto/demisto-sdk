from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook]


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
            if (
                content_item.data.get("issilent")
                or any(
                    content_item.data.get(key, "").startswith("silent")
                    for key in ["name", "id"]
                )
            )
            and not (
                content_item.data.get("issilent")
                and all(
                    content_item.data.get(key, "").startswith("silent")
                    for key in ["name", "id"]
                )
            )
        ]

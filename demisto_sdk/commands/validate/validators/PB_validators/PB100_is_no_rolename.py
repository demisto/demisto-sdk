from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class IsNoRolenameValidator(BaseValidator[ContentTypes]):
    error_code = "PB100"
    description = "Validate whether the playbook has a rolename. If the Playbook has a rolename it is not valid."
    rationale = "The rolename is customisable by users, and should not be pre-set in the marketplace."
    error_message = (
        "The playbook '{playbook_name}' can not have the rolename field, remove it."
    )
    related_field = "rolename"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    playbook_name=content_item.name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.data.get("rolename", None)
        ]

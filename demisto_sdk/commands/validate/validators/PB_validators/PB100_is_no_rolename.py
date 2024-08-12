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
    rationale = "We shouldn't ship playbooks with a role set as this is customisable by the customer."
    error_message = "The playbook '{playbook_name}' can not have a rolename, please remove the field."
    related_field = "rolename"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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

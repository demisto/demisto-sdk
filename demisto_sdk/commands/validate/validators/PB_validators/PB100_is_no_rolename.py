from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook


class IsNoRolenameValidator(BaseValidator[ContentTypes]):
    error_code = "PB100"
    description = "Validate whether the playbook has a rolename. If the Playbook has a rolename it is not valid."
    error_message = "The playbook '{playbook_name}' can not have a rolename, please remove the field."
    fix_message = (
        "Removed the 'rolename' from the following playbook '{playbook_name}'."
    )
    related_field = "rolename"
    is_auto_fixable = True

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

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.data.pop("rolename", None)
        return FixResult(
            validator=self,
            message=self.fix_message.format(playbook_name=content_item.name),
            content_object=content_item,
        )

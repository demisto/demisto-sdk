from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class ScriptRunAsIsNotDBotRoleValidator(BaseValidator[ContentTypes]):
    error_code = "SC106"
    description = "Checks that the script runas is not equal to DBotRole"
    rationale = (
        "When using the DBotRole as default permission, one might give place for privilege escalation by mistake. "
        "Meaning, an analyst might see incidents he should not be able to see by running an automation with these permissions. "
        "Therefore, we only allow this role as default when no sensitive data can be returned. "
        "This helps maintain the security and integrity of the system by preventing unauthorized access to sensitive data."
    )
    error_message = "The script {0} runas field = DBotRole, it may cause access and exposure of sensitive data."
    related_field = "runas"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.docker_image),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.runas == "DBotRole"
        ]

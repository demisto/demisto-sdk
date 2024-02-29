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
    rationale = "For security reasons, the `runas` field should not be set to DBotRole."
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

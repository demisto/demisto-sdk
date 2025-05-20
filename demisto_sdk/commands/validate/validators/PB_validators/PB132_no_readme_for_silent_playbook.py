from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class NoReadmeForSilentPlaybook(BaseValidator[ContentTypes]):
    error_code = "PB132"
    description = "A silent playbook is not allowed to have a README file."
    rationale = "To ensure that silent playbooks do not appears in the documentation."
    error_message = "A silent playbook is not allowed to have a README file."
    related_field = "issilent"
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
            if content_item.is_silent and content_item.readme.exist
        ]

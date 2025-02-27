from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook

DEPRECATED_DESC_REGEX = r"Deprecated\.\s*(.*?Use .*? instead\.*?)"
DEPRECATED_NO_REPLACE_DESC_REGEX = r"Deprecated\.\s*(.*?No available replacement\.*?)"


class DeprecatedDescriptionValidator(BaseValidator[ContentTypes]):
    error_code = "PB104"
    description = "Validate whether a deprecated playbook has a valid description."
    rationale = "Description of deprecated content should be consistent."
    run_on_deprecated = True
    error_message = (
        "The deprecated playbook '{playbook_name}' has invalid description.\n"
        "The description of all deprecated playbooks should follow one of the formats:\n"
        '1. "Deprecated. Use PLAYBOOK_NAME instead."\n'
        '2. "Deprecated. REASON No available replacement."'
    )
    related_field = "description"
    is_auto_fixable = False

    @staticmethod
    def _is_deprecated_with_invalid_description(content_item: ContentTypes) -> bool:
        is_deprecated = content_item.deprecated
        description = content_item.description or ""

        if is_deprecated and not any(
            re.search(pattern, description)
            for pattern in [DEPRECATED_DESC_REGEX, DEPRECATED_NO_REPLACE_DESC_REGEX]
        ):
            return True

        return False

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
            if self._is_deprecated_with_invalid_description(content_item)
        ]

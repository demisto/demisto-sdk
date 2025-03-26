from __future__ import annotations

import re
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Script, Integration]


class IsDeprecatedCorrectlyValidator(BaseValidator[ContentTypes]):
    error_code = "BA126"
    description = "Checks if script/integration is deprecated correctly"
    rationale = (
        "Deprecated scripts/integrations need clear descriptions for user guidance. "
        "For deprecation process, see: "
        "https://xsoar.pan.dev/docs/reference/articles/deprecation-process-and-hidden-packs#how-to-deprecate-and-hide-a-pack"
    )
    error_message = (
        "The description of all deprecated {0} should follow one of the formats:"
        '1. "Deprecated. Use CONTENT_ITEM_NAME instead."'
        '2. "Deprecated. REASON No available replacement."'
    )
    related_field = "description, comment"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.content_type),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.deprecated
            and not any(
                (
                    re.search(DEPRECATED_DESC_REGEX, content_item.description),  # type: ignore[arg-type]
                    re.search(
                        DEPRECATED_NO_REPLACE_DESC_REGEX,
                        content_item.description,  # type: ignore[arg-type]
                    ),
                )
            )
        ]

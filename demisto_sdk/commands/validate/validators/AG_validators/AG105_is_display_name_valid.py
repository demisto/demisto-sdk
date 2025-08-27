from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class IsDisplayNameValidValidator(BaseValidator[ContentTypes]):
    error_code = "AG105"
    description = "Ensure that the display field is in the required format."
    rationale = "Display names must be user-friendly and conform to standards."
    error_message = "The following display name values are invalid: {0}"
    related_field = "display"
    is_auto_fixable = False

    # AgentixAction display_name must start with a letter (either lower or upper case) and contain only
    # the following characters: lowercase letters, uppercase letters, digits, underscores, hyphens, spaces.
    AGENTIX_ACTION_DISPLAY_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_\- ]*$")

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            valid = True
            display_name = getattr(content_item, "display_name", None)
            if not display_name:
                continue
            if isinstance(content_item, AgentixAction):
                if not self.AGENTIX_ACTION_DISPLAY_NAME_PATTERN.match(display_name):
                    valid = False
            if not valid:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            display_name,
                        ),
                        content_object=content_item,
                    )
                )
        return validation_results

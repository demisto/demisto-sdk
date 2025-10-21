from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAgent


class IsValidColorValidator(BaseValidator[ContentTypes]):
    error_code = "AG104"
    description = "Validate that the Agentix-agent color is a valid RGB hex color."
    rationale = "The color field must be a valid RGB hex color string to be displayed correctly in the UI."
    error_message = (
        "The Agentix-agent '{0}' color '{1}' is not a valid RGB hex color.\n"
        "Please make sure that the color is a valid 6-digit hex color string, starting with '#'. For example: '#FFFFFF'."
    )
    related_field = "color"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    content_item.color,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not self.is_valid_color(content_item.color)
        ]

    def is_valid_color(self, color: str) -> bool:
        """Checks if a string is a valid hex color."""
        return bool(re.match(r"^#[0-9a-fA-F]{6}$", color))

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAgent
LIMIT = 65535

class IsSystemInstructionsValidValidator(BaseValidator[ContentTypes]):
    error_code = "AG109"
    description = f"AgentixAgent system instructions must not exceed {LIMIT} bytes."
    rationale = f"System instructions have a size limit of {LIMIT} bytes."
    error_message = "The system instructions for Agentix Agent '{0}' exceed the maximum allowed size of {2} bytes (current size: {1} bytes)."

    related_field = "systeminstructions"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            system_instructions = getattr(content_item, "systeminstructions", "")
            if not system_instructions:
                continue

            # Calculate size in bytes
            size_in_bytes = len(system_instructions.encode("utf-8"))

            if size_in_bytes > LIMIT:
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.name,
                            size_in_bytes,
                            LIMIT
                        ),
                        content_object=content_item,
                    )
                )
        return validation_results

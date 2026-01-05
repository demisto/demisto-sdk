from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAgent


class IsSystemInstructionsFileExistsValidator(BaseValidator[ContentTypes]):
    error_code = "AG104"
    description = "Checks if the AgentixAgent has a system instructions file."
    error_message = (
        "The AgentixAgent '{0}' is missing a system instructions file. "
        "Please create a file named '{1}_systeminstructions.md' in the agent's directory."
    )
    related_field = "systeminstructions"
    rationale = (
        "AgentixAgent system instructions should be stored in a separate file "
        "for better maintainability and readability."
    )
    related_file_type = [RelatedFileType.SYSTEM_INSTRUCTIONS]
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    content_item.path.parent.name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.system_instructions_file.exist
        ]
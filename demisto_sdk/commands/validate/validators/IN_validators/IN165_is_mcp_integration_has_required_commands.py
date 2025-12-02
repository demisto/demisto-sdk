from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsMCPIntegrationHasRequiredCommandsValidator(BaseValidator[ContentTypes]):
    error_code = "IN165"
    description = "Validate that if an integration has ismcp: true, it must have 'list-tools' and 'call-tool' commands."
    rationale = "Integrations marked as MCP (Model Context Protocol) must implement specific commands to function correctly within the MCP framework."
    error_message = "The integration is marked as MCP (ismcp: true) but is missing the following required commands: {0}."
    related_field = "ismcp"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        mcp_required_commands = {"list-tools", "call-tool"}

        results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.is_mcp:
                existing_commands = {command.name for command in content_item.commands}
                missing_commands = mcp_required_commands.difference(existing_commands)
                if missing_commands:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                ", ".join(sorted(missing_commands))
                            ),
                            content_object=content_item,
                        )
                    )
        return results

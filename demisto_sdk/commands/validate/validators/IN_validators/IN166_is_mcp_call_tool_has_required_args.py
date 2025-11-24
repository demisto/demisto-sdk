from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsMCPCallToolHasRequiredArgsValidator(BaseValidator[ContentTypes]):
    error_code = "IN166"
    description = "Validate that if an integration has ismcp: true, its 'call-tool' command must have 'name' and 'arguments' arguments."
    rationale = "The 'call-tool' command in MCP integrations requires specific arguments ('name' and 'arguments') to function correctly within the MCP framework."
    error_message = "The integration is marked as MCP (ismcp: true) but its 'call-tool' command is missing the following required arguments: {0}."
    related_field = "ismcp"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        required_call_tool_args = {"name", "arguments"}

        for content_item in content_items:
            if content_item.is_mcp:
                call_tool_command = next(
                    (
                        command
                        for command in content_item.commands
                        if command.name == "call-tool"
                    ),
                    None,
                )

                if call_tool_command:
                    existing_args = {arg.name for arg in call_tool_command.args}
                    missing_args = required_call_tool_args.difference(existing_args)

                    if missing_args:
                        results.append(
                            ValidationResult(
                                validator=self,
                                message=self.error_message.format(
                                    ", ".join(sorted(missing_args))
                                ),
                                content_object=content_item,
                            )
                        )
        return results

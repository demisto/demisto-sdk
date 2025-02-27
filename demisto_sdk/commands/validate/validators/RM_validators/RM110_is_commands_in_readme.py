from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    INCIDENT_COMMANDS,
    MIRRORING_COMMANDS,
    GitStatuses,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration
COMMANDS_EXCLUDED_FROM_README_DOCUMENTATION = MIRRORING_COMMANDS + INCIDENT_COMMANDS


class IsCommandsInReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM110"
    description = "Validates that all commands are mentioned in the README file"
    rationale = "Ensuring all commands are documented in the README helps users understand the available functionality"
    error_message = (
        "The following commands appear in the YML file but not in the README file: {}."
    )
    related_field = "commands"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            undocumented_commands = [
                command.name
                for command in content_item.commands
                if command.name not in content_item.readme.file_content
                and command.name not in COMMANDS_EXCLUDED_FROM_README_DOCUMENTATION
                and not command.deprecated
                and not command.hidden
                and not command.name.endswith("get-indicators")
            ]
            if undocumented_commands:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(undocumented_commands)
                        ),
                        content_object=content_item,
                        path=content_item.readme.file_path,
                    )
                )
        return results

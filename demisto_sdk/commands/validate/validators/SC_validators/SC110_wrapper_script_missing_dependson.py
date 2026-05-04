from __future__ import annotations

import re
from typing import Iterable, List, Set

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.base_script import (
    EXECUTE_CMD_PATTERN,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

# Also captures execute_polling_command("cmd-name", ...)
EXECUTE_POLLING_CMD_PATTERN = re.compile(
    r"execute_polling_command\(['\"]([a-zA-Z-_]+)['\"].*", re.IGNORECASE
)

ContentTypes = Script


class WrapperScriptMissingDependsOnValidator(BaseValidator[ContentTypes]):
    error_code = "SC110"
    description = (
        "Validates that wrapper scripts declare all commands/scripts they call via "
        "executeCommand in the 'dependson' field."
    )
    rationale = (
        "The 'dependson' field is used to build pack dependency graphs and ensure "
        "that all required content items are available at runtime. Wrapper scripts "
        "that call other commands/scripts via executeCommand must declare those "
        "dependencies explicitly so the platform can resolve them correctly."
    )
    error_message = (
        "Script '{name}' calls the following commands/scripts via executeCommand "
        "but does not list them in 'dependson.must' or 'dependson.should': {missing}. "
        "Add them under 'dependson.must' or 'dependson.should' in the script's YAML."
    )
    related_field = "dependson"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """
        Identify scripts that call commands/scripts via executeCommand but do not
        declare them in the 'dependson' field (either 'must' or 'should').

        Args:
            content_items (Iterable[ContentTypes]): A list of Script objects to validate.

        Returns:
            List[ValidationResult]: A list of validation results for scripts that are
                missing dependson declarations for commands they call.
        """
        results: List[ValidationResult] = []

        for content_item in content_items:
            # LLM scripts have no code to parse
            if content_item.is_llm:
                continue

            code = content_item.code
            if not code:
                continue

            called_commands = self._get_called_commands(code)
            if not called_commands:
                continue

            declared_depends_on = self._get_declared_depends_on(content_item)
            missing = called_commands - declared_depends_on

            if missing:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            name=content_item.name,
                            missing=", ".join(sorted(missing)),
                        ),
                        content_object=content_item,
                    )
                )

        return results

    @staticmethod
    def _get_called_commands(code: str) -> Set[str]:
        """
        Extract all command/script names called via executeCommand from the script code.
        Reuses the same regex pattern as BaseScriptParser.get_command_executions().

        Args:
            code (str): The script source code.

        Returns:
            Set[str]: A set of command/script names called via executeCommand.
        """
        return set(EXECUTE_CMD_PATTERN.findall(code)) | set(
            EXECUTE_POLLING_CMD_PATTERN.findall(code)
        )

    @staticmethod
    def _get_declared_depends_on(content_item: ContentTypes) -> Set[str]:
        """
        Extract all command/script names declared in the 'dependson' field
        (both 'must' and 'should' sections) using the already-loaded YAML data
        from the content item, without re-reading the file from disk.

        Strips the optional pipe-separated pack prefix
        (e.g. 'MyPack|my-command' → 'my-command').

        Args:
            content_item (ContentTypes): The Script object to inspect.

        Returns:
            Set[str]: A set of declared command/script names (without pack prefix).
        """
        depends_on_data = content_item.data.get("dependson", {}) or {}
        must: List[str] = depends_on_data.get("must", []) or []
        should: List[str] = depends_on_data.get("should", []) or []
        all_entries = list(must) + list(should)
        # Strip optional pack-prefix (e.g. "MyPack|my-command" → "my-command")
        return {entry.split("|")[-1] for entry in all_entries if entry}

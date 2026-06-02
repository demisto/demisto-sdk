from __future__ import annotations

import re
from abc import ABC
from typing import Iterable, List, Set

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.base_script import (
    EXECUTE_CMD_PATTERN,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

EXECUTE_POLLING_CMD_PATTERN = re.compile(
    r"execute_polling_command\(['\"]([a-zA-Z-_]+)['\"].*", re.IGNORECASE
)
ContentTypes = Script


class WrapperScriptMissingDependsOnValidator(BaseValidator[ContentTypes], ABC):
    error_code = "SC110"
    description = (
        "Validates that wrapper scripts (those wrapped by an AgentixAction) declare "
        "all commands/scripts they call via executeCommand in the 'dependson' field. "
        "Note: the check is not recursive — it only inspects commands/scripts called "
        "directly by the current script, and does not traverse into scripts that are "
        "themselves executed by the current script."
    )
    rationale = (
        "The 'dependson' field is used to build pack dependency graphs and ensure "
        "that all required content items are available at runtime. Wrapper scripts "
        "that call other commands/scripts via executeCommand must declare those "
        "dependencies explicitly so the platform can resolve them correctly."
    )
    error_message = (
        "Script '{name}' calls the following commands/scripts via executeCommand "
        "but does not list them in 'dependson': {missing}. "
        "Add them under 'dependson.must' or 'dependson.should' in the script's YAML."
    )
    related_field = "dependson"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self,
        content_items: Iterable[ContentTypes],
        validate_all_files: bool,
    ) -> List[ValidationResult]:
        """
        Identify scripts that are wrapped by an AgentixAction and call
        commands/scripts via executeCommand but do not declare them in the
        'dependson' field (either 'must' or 'should').

        Only scripts that have at least one AgentixAction wrapping them
        (underlyingcontentitem.type == 'script') are validated.
        The set of wrapped scripts is obtained from the content graph.

        Args:
            content_items (Iterable[ContentTypes]): A list of Script objects to validate.
            validate_all_files (bool): When True, query the graph for *all* AgentixActions
                (ignoring the current changeset) so that wrapped scripts are detected even
                when only the script itself changed and the wrapping AgentixAction did not.
                When False, only the IDs of the scripts present in ``content_items`` are
                queried — sufficient for changed-files / git execution modes.

        Returns:
            List[ValidationResult]: A list of validation results for scripts that are
                missing dependson declarations for commands they call.
        """
        content_items_list = list(content_items)
        if not content_items_list:
            return []

        items_by_id = {item.object_id: item for item in content_items_list}

        # Ask the graph which scripts are wrapped by an AgentixAction.
        # - validate_all_files=True  -> [] means "return all AgentixActions"
        # - validate_all_files=False -> restrict the query to the IDs we care about
        query_ids: List[str] = (
            [] if validate_all_files else list(items_by_id.keys())
        )
        actions: List[AgentixAction] = (
            self.graph.get_agentix_actions_using_content_items(query_ids)
        )

        wrapped_ids: Set[str] = {
            action.underlying_content_item_id
            for action in actions
            if action.underlying_content_item_type == "script"
            and action.underlying_content_item_id
            and action.underlying_content_item_id in items_by_id
        }

        logger.debug(
            f"SC110: {len(wrapped_ids)} of {len(items_by_id)} script(s) in scope "
            f"are wrapped by an AgentixAction: {sorted(wrapped_ids)}"
        )

        results: List[ValidationResult] = []
        for script_id in wrapped_ids:
            content_item = items_by_id[script_id]

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

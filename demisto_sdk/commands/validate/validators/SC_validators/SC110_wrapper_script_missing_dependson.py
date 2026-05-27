from __future__ import annotations

import re

from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.logger import logger
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


class WrapperScriptMissingDependsOnValidator(BaseValidator[ContentTypes]):
    error_code = "SC110"
    description = (
        "Validates that wrapper scripts (those wrapped by an AgentixAction) declare "
        "all commands/scripts they call via executeCommand in the 'dependson' field."
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

    # Class-level cache for wrapped script IDs (populated once per validation run)
    _wrapped_script_ids_cache: Optional[Set[str]] = None

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        """
        Identify scripts that are wrapped by an AgentixAction and call
        commands/scripts via executeCommand but do not declare them in the
        'dependson' field (either 'must' or 'should').

        Only scripts that have at least one AgentixAction wrapping them
        (underlyingcontentitem.type == 'script') are validated.
        Uses the content graph to determine which scripts are wrapped.

        Args:
            content_items (Iterable[ContentTypes]): A list of Script objects to validate.

        Returns:
            List[ValidationResult]: A list of validation results for scripts that are
                missing dependson declarations for commands they call.
        """
        results: List[ValidationResult] = []
        content_items_list = list(content_items)

        if not content_items_list:
            return results

        # Build the set of script IDs wrapped by AgentixActions (cached)
        wrapped_ids = self._get_action_wrapped_script_ids(content_items_list)

        for content_item in content_items_list:
            # Only validate scripts that are wrapped by an AgentixAction
            if content_item.object_id not in wrapped_ids:
                logger.debug(
                    f"SC110: Skipping script '{content_item.name}' "
                    f"(id={content_item.object_id}) — not wrapped by any AgentixAction."
                )
                continue

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
            logger.debug(f"called_commands are {called_commands}, declared_dependson are: {declared_depends_on}. {missing=}.")

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

    @classmethod
    def _get_action_wrapped_script_ids(
        cls, content_items: List[ContentTypes]
    ) -> Set[str]:
        """
        Build a set of script IDs that are wrapped by at least one AgentixAction.

        Uses the content graph to query for AgentixActions that have a USES
        relationship to the given scripts.

        The result is cached at the class level so it is only computed once per
        validation run.

        Args:
            content_items: The list of Script content items being validated.

        Returns:
            Set[str]: A set of script IDs that are wrapped by AgentixActions.
        """
        if cls._wrapped_script_ids_cache is not None:
            return cls._wrapped_script_ids_cache

        script_ids = [item.object_id for item in content_items]
        wrapped_ids: Set[str] = set()

        try:
            if not cls.graph_interface:
                logger.debug(
                    "SC110: Graph not available, falling back to validating all scripts."
                )
                wrapped_ids = set(script_ids)
            else:
                # Query the graph for AgentixActions that use these scripts
                actions = cls.graph_interface.get_agentix_actions_using_content_items(
                    script_ids
                )

                # Extract the script IDs that have at least one wrapping action
                for action in actions:
                    underlying_id = getattr(action, "underlying_content_item_id", None)
                    if underlying_id and underlying_id in script_ids:
                        wrapped_ids.add(underlying_id)

                logger.debug(
                    f"SC110: Found {len(wrapped_ids)} script(s) wrapped by "
                    f"AgentixActions (out of {len(script_ids)} checked): "
                    f"{sorted(wrapped_ids)}"
                )
        except Exception:
            logger.debug(
                "SC110: Graph lookup failed, falling back to validating all scripts.",
                exc_info=True,
            )
            wrapped_ids = set(script_ids)

        cls._wrapped_script_ids_cache = wrapped_ids
        return wrapped_ids

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

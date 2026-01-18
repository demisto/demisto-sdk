from __future__ import annotations

import re
from abc import ABC
from typing import Iterable, List, Optional, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_action import (
    AgentixActionArgument,
    AgentixActionOutput,
)
from demisto_sdk.commands.content_graph.objects.ai_prompt import AIPrompt
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAction, Integration, Script, Playbook, AIPrompt]


def replace_alerts_with_incidents(text: str) -> str:
    def replacer(match):
        word = match.group()
        replacement = "incidents" if word.lower() == "alerts" else "incident"
        # Match the original casing
        if word.isupper():
            return replacement.upper()
        elif word[0].isupper():
            return replacement.capitalize()
        else:
            return replacement

    # Match case-insensitive "alert" or "alerts"
    return re.sub(r"alerts?", replacer, text, flags=re.IGNORECASE)


class IsAgentixActionUsingExistingContentItemValidator(
    BaseValidator[ContentTypes], ABC
):
    error_code = "GR110"
    description = (
        "Validates that Agentix actions reference existing commands/scripts/playbooks/prompts "
        "and use valid inputs/outputs with matching UI names."
    )
    rationale = (
        "Prevents runtime errors by ensuring Agentix actions only reference "
        "existing content items and valid inputs/outputs."
    )
    error_message = ""
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        """
        Main entry point: validate AgentixActions and their underlying content.
        Handles changed actions and changed Integrations/Scripts/Playbooks.
        """
        results: List[ValidationResult] = []

        agentix_actions_to_validate = set()
        changed_underlying_items = []

        # When validate_all_files=True, get all AgentixActions from graph
        if validate_all_files:
            all_actions = self.graph.get_agentix_actions_using_content_items([])
            agentix_actions_to_validate.update(all_actions)
        else:
            # Only validate specific items from content_items
            for item in content_items:
                if isinstance(item, AgentixAction):
                    agentix_actions_to_validate.add(item)
                elif isinstance(item, (Integration, Script, Playbook, AIPrompt)):
                    changed_underlying_items.append(item)

            # Add dependent actions if underlying content changed
            if changed_underlying_items:
                dependent_actions = self.graph.get_agentix_actions_using_content_items(
                    [u.object_id for u in changed_underlying_items]
                )
                agentix_actions_to_validate.update(dependent_actions)

        for action in agentix_actions_to_validate:
            action_type = action.underlying_content_item_type

            if action_type not in {"command", "script", "playbook", "prompt"}:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"The action '{action.name}' wraps a content type '{action_type}', "
                            "which is currently unsupported in Agentix. Only 'command', 'script', 'playbook', and 'prompt' types are allowed."
                        ),
                        content_object=action,
                    )
                )
                continue

            item_name: str = (
                action.underlying_content_item_command or ""
                if action_type == "command"
                else action.underlying_content_item_id or ""
            )
            integration_or_script_id = action.underlying_content_item_id or ""

            if integration_or_script_id in {"_any_", "_builtin_"}:
                # Actions that wrap built-in or enrich commands are not validated
                continue

            # Resolve the underlying content item
            underlying_item = self._get_underlying_item(
                action, item_name, action_type, changed_underlying_items
            )

            # Try replacing "alerts" with "incidents" if not found
            if not underlying_item:
                replaced_name = replace_alerts_with_incidents(item_name)
                if replaced_name != item_name:
                    item_name = replaced_name
                    underlying_item = self._get_underlying_item(
                        action, item_name, action_type, changed_underlying_items
                    )

            # Still not found? search the graph
            if not underlying_item:
                graph_result = self.graph.search(object_id=item_name)
                underlying_item = self._get_underlying_item(
                    action,
                    item_name,
                    action_type,
                    changed_underlying_items,
                    graph_result,
                )

            if not underlying_item:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"The content item '{item_name}' could not be found in the Content repository. "
                            "Ensure the referenced command, playbook, or script exists."
                        ),
                        content_object=action,
                    )
                )
                continue

            # Validate inputs and outputs
            results.extend(
                self.validate_inputs(action, underlying_item, action_type, item_name)
            )
            results.extend(
                self.validate_outputs(action, underlying_item, action_type, item_name)
            )

        return results

    def _get_underlying_item(
        self,
        action: AgentixAction,
        item_name: str,
        action_type: str,
        changed_underlying: list,
        graph_result: Optional[List] = None,
    ) -> Optional[Integration | Script | Playbook | AIPrompt]:
        """
        Resolve underlying content item for an Agentix action.
        Priority:
        1. Check in changed_underlying items to avoid graph queries.
        2. If graph_result provided, pick correct item from search results.
        Handles:
        - Commands: return Integration containing the command.
        - Scripts/Playbooks/Prompts: return item directly.
        """
        # Check in changed items first
        for item in changed_underlying:
            if action_type in {"script", "playbook", "prompt"} and item.object_id == item_name:
                return item
            elif action_type == "command" and isinstance(item, Integration):
                commands = item.data.get("script", {}).get("commands", [])
                if any(c.get("name") == item_name for c in commands):
                    return item

        # Check graph result if provided
        if graph_result:
            if action_type == "command":
                for item in graph_result:
                    if item.content_type == ContentType.COMMAND:
                        for integration in item.integrations:
                            if (
                                integration.object_id
                                == action.underlying_content_item_id
                            ):
                                return integration
            else:  # script/playbook/prompt
                return graph_result[0] if graph_result else None

        return None

    def _get_command_data(self, underlying_item: Integration, item_name: str) -> dict:
        """Extract command data from integration."""
        if not hasattr(underlying_item, "data"):
            return {}
        commands = underlying_item.data.get("script", {}).get("commands", [])
        return next((cmd for cmd in commands if cmd.get("name") == item_name), {})

    def _get_underlying_arguments(
        self,
        underlying_item: Integration | Script | Playbook | AIPrompt,
        content_item_type: str,
        item_name: str,
    ) -> dict:
        """Extract underlying arguments/inputs based on content type."""
        if content_item_type == "playbook":
            # Extract inputs from playbook
            if isinstance(underlying_item, Playbook):
                if hasattr(underlying_item, "data"):
                    inputs = underlying_item.data.get("inputs", [])
                    # Playbook inputs use 'key' instead of 'name'
                    return {inp.get("key"): inp for inp in inputs if inp.get("key")}
            return {}

        if content_item_type == "command":
            if isinstance(underlying_item, Integration):
                command_data = self._get_command_data(underlying_item, item_name)  # type: ignore[arg-type]
                args = command_data.get("arguments", [])
                return {arg["name"]: arg for arg in args}
            return {}

        if content_item_type == "prompt":
            # Extract arguments from AIPrompt
            if isinstance(underlying_item, AIPrompt):
                if hasattr(underlying_item, "arguments") and underlying_item.arguments:
                    return {arg.name: arg for arg in underlying_item.arguments}
                elif hasattr(underlying_item, "data"):
                    args = underlying_item.data.get("args", [])
                    return {arg["name"]: arg for arg in args}
            return {}

        # script
        if isinstance(underlying_item, Script):
            if hasattr(underlying_item, "data"):
                args = underlying_item.data.get("args", [])
                return {arg["name"]: arg for arg in args}
        return {}

    def _get_underlying_outputs(
        self,
        underlying_item: Integration | Script | Playbook | AIPrompt,
        content_item_type: str,
        item_name: str,
    ) -> dict:
        """Extract underlying outputs based on content type."""
        if content_item_type == "playbook":
            # Extract outputs from playbook
            if isinstance(underlying_item, Playbook):
                if hasattr(underlying_item, "data"):
                    outputs = underlying_item.data.get("outputs", [])
                    # Playbook outputs use 'contextPath' like scripts/commands
                    return {
                        out.get("contextPath"): out
                        for out in outputs
                        if out.get("contextPath")
                    }
            return {}

        if content_item_type == "command":
            command_data = self._get_command_data(underlying_item, item_name)  # type: ignore[arg-type]
            outputs = command_data.get("outputs", [])
            return {
                out.get("contextPath"): out for out in outputs if out.get("contextPath")
            }

        if content_item_type == "prompt":
            # Extract outputs from AIPrompt
            if isinstance(underlying_item, AIPrompt):
                if hasattr(underlying_item, "outputs") and underlying_item.outputs:
                    return {out.contextPath: out for out in underlying_item.outputs}
                elif hasattr(underlying_item, "data"):
                    outputs = underlying_item.data.get("outputs", [])
                    return {
                        out.get("contextPath"): out
                        for out in outputs
                        if out.get("contextPath")
                    }
            return {}

        # script
        if isinstance(underlying_item, Script):
            if hasattr(underlying_item, "data"):
                outputs = underlying_item.data.get("outputs", [])
                return {
                    out.get("contextPath"): out
                    for out in outputs
                    if out.get("contextPath")
                }
        return {}

    def _create_validation_error(
        self, content_item: AgentixAction, message: str
    ) -> ValidationResult:
        return ValidationResult(
            validator=self,
            message=message,
            content_object=content_item,
        )

    def _validate_references(
        self,
        content_item: AgentixAction,
        references: list,
        underlying_map: dict,
        reference_type: str,
        content_item_type: str,
        item_name: str,
    ) -> List[ValidationResult]:
        """Generic validation for inputs/outputs."""
        if not underlying_map:
            return []

        results = []
        underlying_type = "argument" if reference_type == "input" else "output"

        for ref in references:
            ref_name = ref.name
            underlying_name = (
                ref.content_item_arg_name
                if reference_type == "input"
                else ref.content_item_output_name
            )

            if underlying_name not in underlying_map:
                message = (
                    f"Action '{content_item.name}' {reference_type} '{ref_name}' references "
                    f"underlying {underlying_type} '{underlying_name}' "
                    f"not found in {content_item_type} '{item_name}'."
                )
                results.append(self._create_validation_error(content_item, message))

            if ref_name != underlying_name:
                message = (
                    f"Action '{content_item.name}' {reference_type} UI name '{ref_name}' "
                    f"must match underlying name '{underlying_name}'."
                )
                results.append(self._create_validation_error(content_item, message))

        return results

    def validate_inputs(
        self,
        content_item: AgentixAction,
        underlying_item: Integration | Script | Playbook | AIPrompt,
        content_item_type: str,
        item_name: str,
    ) -> List[ValidationResult]:
        """Validate AgentixAction inputs reference underlying args."""
        underlying_args = self._get_underlying_arguments(
            underlying_item, content_item_type, item_name
        )

        action_args = content_item.args
        if not action_args and hasattr(content_item, "data"):
            args_data = content_item.data.get("args", [])
            action_args = [AgentixActionArgument(**arg) for arg in args_data]

        return self._validate_references(
            content_item,
            action_args or [],
            underlying_args,
            "input",
            content_item_type,
            item_name,
        )

    def validate_outputs(
        self,
        content_item: AgentixAction,
        underlying_item: Integration | Script | Playbook | AIPrompt,
        content_item_type: str,
        item_name: str,
    ) -> List[ValidationResult]:
        """Validate AgentixAction outputs reference underlying outputs."""
        underlying_outputs = self._get_underlying_outputs(
            underlying_item, content_item_type, item_name
        )

        action_outputs = content_item.outputs
        if not action_outputs and hasattr(content_item, "data"):
            outputs_data = content_item.data.get("outputs", [])
            action_outputs = [AgentixActionOutput(**out) for out in outputs_data]

        return self._validate_references(
            content_item,
            action_outputs or [],
            underlying_outputs,
            "output",
            content_item_type,
            item_name,
        )

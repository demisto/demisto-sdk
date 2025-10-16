from __future__ import annotations

import re
from abc import ABC
from typing import Iterable, List, Optional, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAction, Integration, Script]


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
        "Validates that Agentix actions reference existing commands/scripts "
        "with valid inputs/outputs, and that input UI names match the "
        "underlying argument names."
    )
    rationale = (
        "Prevents runtime errors by ensuring Agentix actions only reference "
        "existing content items and their valid inputs/outputs."
    )
    error_message = ""
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        agentix_actions_to_validate = set()

        for content_item in content_items:
            if isinstance(content_item, AgentixAction):
                agentix_actions_to_validate.add(content_item)

            # If it's an Integration, Script, find dependent AgentixActions
            elif isinstance(content_item, (Integration, Script)):
                for relationship_data in content_item.used_by:
                    dependent_item = relationship_data.content_item_to
                    if dependent_item.content_type == ContentType.AGENTIX_ACTION:
                        agentix_actions_to_validate.add(dependent_item)  # type: ignore[arg-type]

        for content_item in agentix_actions_to_validate:
            content_item_type = content_item.underlying_content_item_type

            if content_item_type not in {
                "command",
                "script",
                "playbook",
            }:  # Validate when the action wraps a command, a script or a playbook
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"The action '{content_item.name}' wraps a content type '{content_item_type}', "
                            "which is currently unsupported in Agentix. Only 'command' and 'script' types are allowed."
                        ),
                        content_object=content_item,
                    )
                )
                continue
            elif content_item_type == "command":
                command_or_script_name = content_item.underlying_content_item_command
            else:  # script or playbook
                command_or_script_name = content_item.underlying_content_item_id

            integration_or_script_id = content_item.underlying_content_item_id

            if integration_or_script_id in {"_any_", "_builtin_"}:
                # Actions that wrap built-in or enrich commands are not validated
                continue

            graph_result = self.graph.search(object_id=command_or_script_name)

            replaced_name = replace_alerts_with_incidents(command_or_script_name)  # type: ignore

            # Check again with incident/s instead of alert/s if some content items appear in a few names
            if not graph_result and command_or_script_name != replaced_name:
                command_or_script_name = replaced_name
                graph_result = self.graph.search(object_id=command_or_script_name)

            if (
                not graph_result
            ):  # the command or the script does not exist in the Content repo
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"The content item '{command_or_script_name}' could not be found in the Content repository. "
                            "Ensure the referenced command or script exists."
                        ),
                        content_object=content_item,
                    )
                )

            else:
                # Get the correct item (Integration for commands, or Script/Playbook directly)
                if not integration_or_script_id or not command_or_script_name:
                    continue
                underlying_item = self._get_correct_item(
                    graph_result, content_item_type, integration_or_script_id
                )

                if not underlying_item:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=(
                                f"The command '{command_or_script_name}' is not correctly related to integration ID "
                                f"'{integration_or_script_id}'. Please verify the correct integration ID."
                            ),
                            content_object=content_item,
                        )
                    )
                else:
                    # Validate inputs and outputs
                    if content_item.args:
                        results.extend(
                            self.validate_inputs(
                                content_item,
                                underlying_item,
                                content_item_type,
                                item_name=command_or_script_name,
                            )
                        )
                    if content_item.outputs:
                        results.extend(
                            self.validate_outputs(
                                content_item,
                                underlying_item,
                                content_item_type,
                                item_name=command_or_script_name,
                            )
                        )

        return results

    def _get_correct_item(
        self, graph_result: List, item_type: str, integration_or_script_id: str
    ) -> Optional[Integration | Script]:
        """Get the correct item from graph_result based on type and integration.

        For commands, returns the Integration since args/outputs are only in Integration.data.
        For scripts/playbooks, returns the item directly which already has args/outputs.
        """
        if item_type == "command":
            for item in graph_result:
                if item.content_type == ContentType.COMMAND:
                    # Find the integration that has this command
                    for integration in item.integrations:
                        if integration.object_id == integration_or_script_id:
                            return integration
        else:  # script or playbook
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
        underlying_item: Integration | Script,
        content_item_type: str,
        item_name: str,
    ) -> dict:
        """Extract underlying arguments/inputs based on content type."""
        if content_item_type == "playbook":
            # Playbook not currently supported, return empty dict
            return {}

        if content_item_type == "command":
            if isinstance(underlying_item, Integration):
                command_data = self._get_command_data(underlying_item, item_name)  # type: ignore[arg-type]
                args = command_data.get("arguments", [])
                return {arg["name"]: arg for arg in args}
            return {}

        # script
        if isinstance(underlying_item, Script):
            return {arg.name: arg for arg in (underlying_item.args or [])}  # type: ignore[union-attr]
        return {}

    def _get_underlying_outputs(
        self,
        underlying_item: Integration | Script,
        content_item_type: str,
        item_name: str,
    ) -> dict:
        """Extract underlying outputs based on content type."""
        if content_item_type == "playbook":
            # Playbook not currently supported, return empty dict
            return {}

        if content_item_type == "command":
            command_data = self._get_command_data(underlying_item, item_name)  # type: ignore[arg-type]
            outputs = command_data.get("outputs", [])
            return {
                out.get("contextPath"): out for out in outputs if out.get("contextPath")
            }

        # script
        return {
            out.contextPath: out  # type: ignore[union-attr]
            for out in (underlying_item.outputs or [])  # type: ignore[union-attr]
            if hasattr(out, "contextPath")
        }

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

            if reference_type == "input" and ref_name != underlying_name:
                message = (
                    f"Action '{content_item.name}' input UI name '{ref_name}' "
                    f"must match underlying name '{underlying_name}'."
                )
                results.append(self._create_validation_error(content_item, message))

        return results

    def validate_inputs(
        self,
        content_item: AgentixAction,
        underlying_item: Integration | Script,
        content_item_type: str,
        item_name: str,
    ) -> List[ValidationResult]:
        """Validate AgentixAction inputs reference underlying args."""
        underlying_args = self._get_underlying_arguments(
            underlying_item, content_item_type, item_name
        )
        return self._validate_references(
            content_item,
            content_item.args or [],
            underlying_args,
            "input",
            content_item_type,
            item_name,
        )

    def validate_outputs(
        self,
        content_item: AgentixAction,
        underlying_item: Integration | Script,
        content_item_type: str,
        item_name: str,
    ) -> List[ValidationResult]:
        """Validate AgentixAction outputs reference underlying outputs."""
        underlying_outputs = self._get_underlying_outputs(
            underlying_item, content_item_type, item_name
        )
        return self._validate_references(
            content_item,
            content_item.outputs or [],
            underlying_outputs,
            "output",
            content_item_type,
            item_name,
        )

from __future__ import annotations

import re
from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAction, Integration, Script, Playbook, Pack]


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
        "Agentix actions must wrap existing commands/scripts and reference "
        "valid inputs/outputs. Input UI names must match underlying names."
    )
    rationale = (
        "Ensures Agentix actions reference existing content and prevents "
        "input/output mismatches."
    )
    error_message = ""
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for content_item in content_items:
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

            elif not self.is_content_item_related_to_correct_pack(
                item_type=content_item_type,
                integration_or_script_id=integration_or_script_id,  # type: ignore
                graph_result=graph_result,
            ):
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
                # Validate inputs and outputs using the correct item
                underlying_item = self._get_correct_item(
                    graph_result, content_item_type, integration_or_script_id
                )
                if underlying_item:
                    if content_item.args:
                        results.extend(
                            self.validate_inputs(
                                content_item, underlying_item, content_item_type
                            )
                        )
                    if content_item.outputs:
                        results.extend(
                            self.validate_outputs(
                                content_item, underlying_item, content_item_type
                            )
                        )

        return results

    def _get_correct_item(
        self, graph_result: List, item_type: str, integration_or_script_id: str
    ):
        """Get the correct item from graph_result based on type and integration."""
        if item_type == "command":
            for item in graph_result:
                if item.content_type == ContentType.COMMAND:
                    if any(
                        integration.object_id == integration_or_script_id
                        for integration in item.integrations
                    ):
                        return item
        else:  # script or playbook
            return graph_result[0] if graph_result else None
        return None

    def is_content_item_related_to_correct_pack(
        self, item_type: str, integration_or_script_id: str, graph_result: List
    ) -> bool:
        return (
            self._get_correct_item(graph_result, item_type, integration_or_script_id)
            is not None
        )

    def validate_inputs(
        self,
        content_item: AgentixAction,
        underlying_item,
        content_item_type: str,
    ) -> List[ValidationResult]:
        """Validate AgentixAction inputs reference underlying args."""
        results: List[ValidationResult] = []

        # Get underlying arguments/inputs
        if content_item_type == "playbook":
            if not (hasattr(underlying_item, "inputs") and underlying_item.inputs):
                return results
            underlying_args = {inp.key: inp for inp in underlying_item.inputs}
        else:  # command or script
            if not (hasattr(underlying_item, "args") and underlying_item.args):
                return results
            underlying_args = {arg.name: arg for arg in underlying_item.args}

        # Check each AgentixAction input
        for action_arg in content_item.args:
            underlying_name = action_arg.content_item_arg_name

            if underlying_name not in underlying_args:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"Action '{content_item.name}' references input "
                            f"'{underlying_name}' not found in "
                            f"{content_item_type} '{underlying_item.object_id}'."
                        ),
                        content_object=content_item,
                    )
                )
            elif action_arg.name != underlying_name:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"Action '{content_item.name}' input UI name "
                            f"'{action_arg.name}' must match underlying name "
                            f"'{underlying_name}'."
                        ),
                        content_object=content_item,
                    )
                )

        return results

    def validate_outputs(
        self,
        content_item: AgentixAction,
        underlying_item,
        content_item_type: str,
    ) -> List[ValidationResult]:
        """Validate AgentixAction outputs reference underlying outputs."""
        results: List[ValidationResult] = []

        if not (hasattr(underlying_item, "outputs") and underlying_item.outputs):
            return results

        # Get underlying outputs
        if content_item_type == "playbook":
            underlying_outputs = {
                out.context_path: out
                for out in underlying_item.outputs
                if hasattr(out, "context_path")
            }
        else:  # command or script
            underlying_outputs = {
                out.contextPath: out
                for out in underlying_item.outputs
                if out.contextPath
            }

        # Check each AgentixAction output
        for action_output in content_item.outputs:
            underlying_name = action_output.content_item_output_name

            if underlying_name not in underlying_outputs:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=(
                            f"Action '{content_item.name}' references output "
                            f"'{underlying_name}' not found in "
                            f"{content_item_type} '{underlying_item.object_id}'."
                        ),
                        content_object=content_item,
                    )
                )

        return results

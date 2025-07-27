from __future__ import annotations

import re
from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


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
        "Avoid creating Agentix actions that wrap non-existent commands or scripts"
    )
    rationale = "Actions in Agentix should wrap only existing commands or scripts"
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

        return results

    def is_content_item_related_to_correct_pack(
        self, item_type: str, integration_or_script_id: str, graph_result: List
    ) -> bool:
        if item_type == "command":
            return any(
                integration.object_id == integration_or_script_id
                for item in graph_result
                if item.content_type == ContentType.COMMAND
                for integration in item.integrations
            )
        elif item_type == "script" or item_type == "playbook":
            return True
        return False

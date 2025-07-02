from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


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
    # expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.YML]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        for content_item in content_items:
            name = content_item.underlying_content_item_name
            content_item_type = content_item.underlying_content_item_type
            pack_id = content_item.underlying_content_item_id

            if pack_id in [
                "_any_",
                "_builtin_",
            ]:  # no validation when the action wraps a builtin or enrich command
                continue

            if content_item_type not in [
                "command",
                "script",
            ]:  # Validate when the action wraps a command or script
                results.append(
                    ValidationResult(
                        validator=self,
                        message=f"The content item {name} is not a command or script so it's still not supported",
                        content_object=content_item,
                    )
                )
                continue

            graph_result = self.graph.search(object_id=name)

            if (
                not graph_result
            ):  # the command or the script does not exist in the Content repo
                results.append(
                    ValidationResult(
                        validator=self,
                        message=f"The content item {name} does not exist in the Content repository",
                        content_object=content_item,
                    )
                )

            elif not self.is_content_item_related_to_the_right_pack(
                content_item_type=content_item_type,
                pack_id=pack_id,
                graph_result=graph_result,
            ):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=f"The action relates the content item '{name}' to this '{pack_id}' pack which is not"
                        f" the right pack",
                        content_object=content_item,
                    )
                )

        return results

    def is_content_item_related_to_the_right_pack(
        self, content_item_type: str, pack_id: str, graph_result: List
    ) -> bool:
        if content_item_type == "command":
            for integration in graph_result[0].integrations:
                if integration.object_id == pack_id:
                    return True
        elif content_item_type == "script":
            for script in graph_result[0].scripts:
                if script.object_id == pack_id:
                    return True

        return False

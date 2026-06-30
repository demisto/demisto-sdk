from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.tools import get_relative_path_from_packs_dir
from demisto_sdk.commands.content_graph.objects.agentix_skill import AgentixSkill
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixSkill


class IsSkillUsingUnknownContentValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR116"
    description = (
        "Validates that an Agentix Skill does not reference unknown content items "
        "(e.g. actions that cannot be found in the repository)."
    )
    rationale = (
        "A skill that references a non-existing action is broken: the "
        "`<action=action-id>` token cannot be resolved during prepare-upload, so "
        "the reference must point to an existing content item. Unlike the generic "
        "GR103 (warning), this is enforced as an error for skills."
    )
    error_message = (
        "Agentix Skill '{0}' is using content items: {1} which cannot be found in "
        "the repository."
    )
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool = False
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        file_paths_to_validate = (
            [
                get_relative_path_from_packs_dir(str(content_item.path))
                for content_item in content_items
            ]
            if not validate_all_files
            else []
        )
        uses_unknown_content = self.graph.get_unknown_content_uses(
            file_paths_to_validate
        )

        for content_item in uses_unknown_content:
            # Restrict GR116 to Agentix Skills only; other content types are
            # covered (as a warning) by GR103.
            if not isinstance(content_item, AgentixSkill):
                continue
            names_of_unknown_items = [
                relationship.content_item_to.object_id
                or relationship.content_item_to.name  # type: ignore[attr-defined]
                for relationship in content_item.uses
            ]
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        content_item.name,
                        ", ".join(f"'{name}'" for name in names_of_unknown_items),
                    ),
                    content_object=content_item,
                )
            )
        return results

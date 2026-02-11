from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.tools import get_core_pack_list
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook]


class IsValidAutonomousPlaybookDependenciesValidator(BaseValidator[ContentTypes], ABC):
    error_code = "AS102"
    description = (
        "Validates that playbooks in autonomous packs only use scripts and "
        "sub-playbooks from core packs or other autonomous packs."
    )
    rationale = (
        "Autonomous packs should be self-contained and only depend on core packs "
        "or other autonomous packs for scripts and sub-playbooks."
    )
    error_message = (
        "Playbook '{0}' is in an autonomous pack but uses the following scripts/sub-playbooks "
        "from non-core, non-autonomous packs: {1}."
    )
    is_auto_fixable = False
    related_field = "tasks"

    def obtain_invalid_content_items_using_graph(
        self,
        content_items: Iterable[ContentTypes],
        validate_all_files: bool = False,
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []

        file_paths_to_validate = (
            [
                str(content_item.path.relative_to(CONTENT_PATH))
                for content_item in content_items
            ]
            if not validate_all_files
            else []
        )

        core_pack_list = get_core_pack_list()
        invalid_playbooks = (
            self.graph.find_autonomous_playbooks_with_invalid_dependencies(
                file_paths_to_validate, core_pack_list
            )
        )

        for content_item in invalid_playbooks:
            invalid_dep_names = [
                relationship.content_item_to.object_id
                or relationship.content_item_to.name
                for relationship in content_item.uses
            ]
            results.append(
                ValidationResult(
                    validator=self,
                    message=self.error_message.format(
                        content_item.name,
                        ", ".join(f"'{name}'" for name in invalid_dep_names),
                    ),
                    content_object=content_item,
                )
            )
        return results

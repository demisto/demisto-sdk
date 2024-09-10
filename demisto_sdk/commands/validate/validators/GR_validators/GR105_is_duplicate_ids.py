from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsDuplicateIdsValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR105"
    description = "Checks for duplicate IDs across content items"
    rationale = (
        "Duplicate IDs can cause conflicts and unpredictable behavior in the system"
    )
    error_message = "Duplicate ID '{}' found in {}"
    related_field = "id"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        validation_resilts = []
        paths_of_content_items_to_validate = (
            [str(item.path) for item in content_items] if not validate_all_files else []
        )
        for content_item, duplicates in self.graph.validate_duplicate_ids(
            paths_of_content_items_to_validate
        ):
            for duplicate in duplicates:
                validation_resilts.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.object_id, duplicate.path
                        ),
                        content_object=content_item,
                    )
                )
        return validation_resilts

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class HaveTheArgsChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC103"
    description = "Check if the argument name has been changed."
    rationale = "If an existing argument has been renamed, it will break backward compatibility."
    error_message = "One or more argument names in the '{file_name}' file have been changed. Please undo the change."
    related_field = "name"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:

            current_args = [arg.name for arg in content_item.args]
            old_args = [arg.name for arg in content_item.old_base_content_object.args]  # type: ignore

            if not set(old_args).issubset(set(current_args)):
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(file_name=content_item.name),
                        content_object=content_item,
                    )
                )

        return results

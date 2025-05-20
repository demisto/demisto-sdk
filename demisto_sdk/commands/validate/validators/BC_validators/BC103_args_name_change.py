from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class ArgsNameChangeValidator(BaseValidator[ContentTypes]):
    error_code = "BC103"
    description = "Check if an argument name has been changed."
    rationale = "If an existing argument has been renamed, it will break backward compatibility."
    error_message = (
        "Possible backward compatibility break: Your updates to this file contain changes "
        "to the names of the following existing arguments: {args}. Please undo the changes."
    )
    related_field = "args.name"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            current_args = [arg.name for arg in content_item.args]
            old_args = [arg.name for arg in content_item.old_base_content_object.args]  # type: ignore
            args_diff = set(old_args) - set(current_args)

            if args_diff:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(args=", ".join(args_diff)),
                        content_object=content_item,
                    )
                )

        return results

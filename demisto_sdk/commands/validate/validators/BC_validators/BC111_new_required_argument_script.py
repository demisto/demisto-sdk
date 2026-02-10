from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


# This validation is similar to BC110, but specifically for scripts.
class NewRequiredArgumentScriptValidator(BaseValidator[ContentTypes]):
    error_code = "BC111"
    description = (
        "Ensure that no new *required* arguments are added to an existing script."
    )
    rationale = "Adding a new required argument or changing a non-required one to required without specifying a default value breaks backward compatibility."
    error_message = "Possible backward compatibility break: You have added the following new *required* arguments: {arg_list}. Please undo the changes."
    related_field = "script.arguments"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        arg_list = []
        for content_item in content_items:
            old_content_item = content_item.old_base_content_object

            arg_list = [
                arg.name
                for arg in content_item.args  # type: ignore
                if arg.required
                and not arg.defaultvalue
                and (
                    not next(
                        (
                            old_arg
                            for old_arg in old_content_item.args  # type: ignore
                            if old_arg.name == arg.name and old_arg.required
                        ),
                        None,
                    )
                )
            ]
            if arg_list:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            arg_list=", ".join(f'"{w}"' for w in arg_list)
                        ),
                        content_object=content_item,
                    )
                )

        return results

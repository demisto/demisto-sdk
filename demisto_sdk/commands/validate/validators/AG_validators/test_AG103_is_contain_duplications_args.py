from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_action import (
    AgentixActionArgument,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class test_IsActionArgsContainDuplicationsValidator(BaseValidator[ContentTypes]):
    error_code = "AG103"
    description = "Prevent duplicate arguments for Agentix Actions."
    rationale = "Duplicate arguments cause confusion and unpredictable behaviors."
    error_message = (
        "The following Agentix action '{0}' contains duplicated arguments:\n{1}\n"
        "Please make sure to remove the duplications."
    )
    related_field = "args"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    f"Argument(s): {duplicated_args_by}, appear(s) multiple times.",
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (duplicated_args_by := self.is_containing_dups(content_item.args))  # type: ignore
        ]

    def is_containing_dups(self, arguments: List[AgentixActionArgument]) -> set:
        appeared_set, duplicated_args = set(), set()
        for argument in arguments:
            if argument.name in appeared_set:
                duplicated_args.add(argument.name)
            else:
                appeared_set.add(argument.name)
        return duplicated_args

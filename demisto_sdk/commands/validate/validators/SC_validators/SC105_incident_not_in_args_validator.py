from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class IsScriptArgumentsContainIncidentWordValidator(BaseValidator[ContentTypes]):
    error_code = "SC105"
    description = "Checks that script arguments do not container the word incident"
    error_message = (
        "The script {0} arguments '{1}' contain the word incident, remove it"
    )
    related_field = "args"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        invalid_content_items = []
        for content_item in content_items:
            wrong_arg_names = []
            for argument in content_item.arguments:
                if "incident" in argument.name:
                    wrong_arg_names.append(argument.name)
            if wrong_arg_names:
                invalid_content_items.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            content_item.name, ", ".join(wrong_arg_names)
                        ),
                        content_object=content_item,
                    )
                )

        return invalid_content_items

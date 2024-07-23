from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.tools import search_substrings_by_line
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]


class IsTemplateInReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM107"
    description = "Checks if there are the generic sentence '%%FILL HERE%%' in the README content."
    rationale = "Ensuring our documentation looks good and professional."
    error_message = "The template '%%FILL HERE%%' exists in the following lines of the README content: {0}."
    related_field = "readme"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        """
        Checks if there are the generic sentence '%%FILL HERE%%' in the README content.

        Return:
            List of ValidationResult that each element has '%%FILL HERE%%' in the README content.
        """
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_lines)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_lines := search_substrings_by_line(
                    phrases_to_search=["%%FILL HERE%%"],
                    text=content_item.readme.file_content,
                )
            )
        ]

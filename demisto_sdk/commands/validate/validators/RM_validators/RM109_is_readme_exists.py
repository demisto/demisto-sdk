from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook]


class IsReadmeExistsValidator(BaseValidator[ContentTypes]):
    error_code = "RM109"
    description = "Validates if there is a readme file for the content item."
    rationale = "Ensure that the content item contains additional information about use-cases, inputs, and outputs."
    error_message = "The {0} '{1}' doesn't have a README file. Please add a README.md file in the content item's directory."
    related_field = "readme"
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.content_type, content_item.name
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.readme.exist) and (not content_item.is_silent)
        ]

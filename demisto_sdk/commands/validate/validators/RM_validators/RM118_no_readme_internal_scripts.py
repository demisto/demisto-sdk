from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Script]


class NoReadmeInternalScripts(BaseValidator[ContentTypes]):
    error_code = "RM118"
    description = "Validates that theres no readme file for internal scripts."
    rationale = "Internal scripts should not have a visible readme in xsoar.pan.dev."
    error_message = "The {0} '{1}' is an internal script. Please remove the README.md file in the content item's directory."
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
            if (
                content_item.content_type == "Script"
                and (
                    getattr(content_item, "is_internal", False)
                    or (getattr(content_item, "is_llm", False))
                )
                and (content_item.readme.exist)
            )
        ]

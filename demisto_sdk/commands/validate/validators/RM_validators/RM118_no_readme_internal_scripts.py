from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class NoReadmeInternalScripts(BaseValidator[Script]):
    error_code = "RM118"
    description = "Validates that there's no readme file for internal scripts."
    rationale = "Internal scripts should not have a visible readme in xsoar.pan.dev."
    error_message = "The script '{0}' is an internal script. Please remove the README.md file in the content item's directory."
    related_field = "readme"
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[Script]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.is_internal or content_item.is_llm)
            and content_item.readme.exist
        ]

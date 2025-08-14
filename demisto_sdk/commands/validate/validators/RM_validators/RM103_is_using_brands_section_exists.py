from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class IsUsingBrandsSectionExistsValidator(BaseValidator[ContentTypes]):
    error_code = "RM103"
    description = (
        'Ensures that aggregated script README contains a "using commands" section.'
    )
    rationale = "Ensuring the commands being used are well documented and transperent to customers."
    error_message = "The script's README.md file is missing a 'using commands' section. Please make sure to add one listing all the brands & commands being used by the script."
    related_field = "readme"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if "## Using commands" not in content_item.readme.file_content
        ]

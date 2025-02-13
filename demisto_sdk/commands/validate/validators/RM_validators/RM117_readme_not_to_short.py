from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack

MINIMUM_README_LENGTH = 30


class NotToShortReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM117"
    description = "Validate that the readme file is not to short."
    error_message = """Your Pack README is too short ({0} chars). Please move its content to the pack description or add more useful information to the Pack README. Pack README files are expected to include a few sentences about the pack and/or images."""
    related_field = "readme"
    rationale = "Ensure better documentation."
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(readme_size),
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if (readme_size := len(content_item.readme.file_content))
            and 1 <= readme_size <= MINIMUM_README_LENGTH
        ]

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
    error_code = "RM116"
    description = "Validate that the readme file is not to short"
    error_message = """Your Pack README is too short ({0} chars). Please move its content to the pack description or add more useful information to the Pack README. Pack README files are expected to include a few sentences about the pack and/or images."""

    related_field = "readme"
    rationale = """Check that the readme files are not to short."""

    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]
    sections: List[str] = []
    readme_size = 0

    def verify_readme_is_not_too_short(self, content_item: ContentTypes):
        self.readme_size = len(content_item.readme.file_content)
        if 1 <= self.readme_size <= MINIMUM_README_LENGTH:
            return True
        return False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(self.readme_size, content_item.path),
                content_object=content_item,
            )
            for content_item in content_items
            if (self.verify_readme_is_not_too_short(content_item))
        ]

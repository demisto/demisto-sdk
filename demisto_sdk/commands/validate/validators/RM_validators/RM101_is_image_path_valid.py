from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import INVALID_IMAGE_PATH_REGEX
from demisto_sdk.commands.common.tools import find_regex_on_data
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]


class IsImagePathValidValidator(BaseValidator[ContentTypes]):
    error_code = "RM101"
    description = "Validate images absolute paths, and prints the suggested path if it's not valid."
    rationale = "In official marketplace content, ensures that the images can be used in the upload flow properly."
    error_message = "Detected the following images URLs which are not raw links: {0}"
    related_field = "readme"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(invalid_urls),
                content_object=content_item,
                path=content_item.readme.file_path,
            )
            for content_item in content_items
            if (invalid_urls := self.is_image_path_valid(content_item))
        ]

    def is_image_path_valid(self, content_item):
        if invalid_paths := find_regex_on_data(
            content_item.readme.file_content, INVALID_IMAGE_PATH_REGEX
        ):
            handled_errors = []
            for path in invalid_paths:
                path = path[2]
                alternative_path = path.replace("blob", "raw")
                handled_errors.append((path, alternative_path))
            return "\n".join(
                f"{error[0]} suggested URL {error[1]}" for error in handled_errors
            )
        return ""

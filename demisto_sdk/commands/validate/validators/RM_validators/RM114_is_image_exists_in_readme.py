from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.tools import (
    extract_image_paths_from_str,
    get_full_image_paths_from_relative,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook]


class IsImageExistsInReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM114"
    description = "Validate README images used in README exist."
    error_message = "The following images do not exist: {0}"
    rationale = "Missing images are not shown in rendered markdown"
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_lines)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                any(
                    invalid_lines := [
                        str(image_path)
                        for image_path in get_full_image_paths_from_relative(
                            content_item.pack_name,
                            extract_image_paths_from_str(
                                text=content_item.readme.file_content
                            ),
                        )
                        if image_path and not image_path.is_file()
                    ]
                )
            )
        ]

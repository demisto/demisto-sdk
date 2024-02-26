
from __future__ import annotations

import re
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.common.tools import extract_image_paths_from_str
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook]


class IsImageExistsInReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM114"
    description = "Validate README images are actually exits."
    error_message = "The following image files does not exists: {0}"
    related_field = ""
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README]
    # expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.ADDED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_lines)),
                content_object=content_item,
            )
            for content_item in content_items

            if (
                any(invalid_lines:=
                    [
                        f"Packs/{content_item.pack_name}/{str(image_path).replace('../', '')}" 
                        if content_item.pack_name not in str(image_path) else str(image_path)
                        for image_path in extract_image_paths_from_str(text=content_item.readme)
                        if image_path and not image_path.is_file()
                    ]
                )
            )
        ]

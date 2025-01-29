from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

CONTRIBUTOR_DETAILED_DESC = "Contributed Integration"

ContentTypes = Integration


class IsDescriptionContainsContribDetailsValidator(BaseValidator[ContentTypes]):
    error_code = "DS105"
    description = "check if DESCRIPTION file contains contribution details."
    rationale = "the contribution/partner details will be generated automatically and we don't want should be duplicate."
    error_message = (
        "Description file ({0}) "
        "contains contribution/partner details that will be generated automatically"
        " when the upload command is performed.\n"
        "Delete any details related to contribution/partner."
    )
    is_auto_fixable = False
    related_file_type = [RelatedFileType.DESCRIPTION_File]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.description_file.file_path.name
                ),
                content_object=content_item,
                path=content_item.description_file.file_path,
            )
            for content_item in content_items
            if re.findall(
                rf"### .* {CONTRIBUTOR_DETAILED_DESC}",
                content_item.description_file.file_content,
            )
        ]

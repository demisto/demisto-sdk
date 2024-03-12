from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.tools import check_text_content_contain_sub_text
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsContainCopyRightSectionValidator(BaseValidator[ContentTypes]):
    error_code = "RM113"
    description = "Validate that non of the readme lines contains the disallowed copyright section keywords."
    rationale = "Content in the Cortex marketplace is licensed under the MIT license."
    error_message = "Invalid keywords related to Copyrights (BSD, MIT, Copyright, proprietary) were found in lines: {0}. Copyright section cannot be part of pack readme."
    related_field = "readme"
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
                invalid_lines := check_text_content_contain_sub_text(
                    sub_text_list=["BSD", "MIT", "Copyright", "proprietary"],
                    to_split=True,
                    text=content_item.readme.file_content,
                )
            )
        ]

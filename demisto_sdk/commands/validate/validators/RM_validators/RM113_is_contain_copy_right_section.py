from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.tools import check_readme_content_contain_text
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsContainCopyRightSectionValidator(BaseValidator[ContentTypes]):
    error_code = "RM113"
    description = "Validate that non of the readme lines contains the disallowed copyright section keywords."
    error_message = "Invalid keywords related to Copyrights (BSD, MIT, Copyright, proprietary) were found in lines: {0}. Copyright section cannot be part of pack readme."
    related_field = "readme"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_lines)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_lines := check_readme_content_contain_text(
                    text_list=["BSD", "MIT", "Copyright", "proprietary"],
                    to_split=True,
                    readme_content=content_item.readme,
                )
            )
        ]

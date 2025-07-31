
from __future__ import annotations

from abc import ABC

from typing import Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        FixResult,
        ValidationResult,
)

ContentTypes = Script


class MandatoryGenericArgumentsAggregatedScriptValidator(BaseValidator[ContentTypes], ABC):
    error_code = "SC101"
    description = ""
    rationale = " We want to ensure that every new Aggregated Script created has the mandatory generic arguments."
    error_message = ""
    fix_message = ""
    related_field = ""
    is_auto_fixable = True
    related_file_type = [RelatedFileType.SCHEMA]

    
    def obtain_invalid_content_items_using_graph(self, content_items: Iterable[ContentTypes], validate_all_files: bool) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
        

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
            

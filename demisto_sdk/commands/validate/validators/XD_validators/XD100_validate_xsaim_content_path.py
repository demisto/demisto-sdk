
from __future__ import annotations

from abc import ABC

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        FixResult,
        ValidationResult,
)
#TODO: make sure we have all relevant types, in all files

ContentTypes = Union[ModelingRule, ParsingRule, CorrelationRule, XSIAMDashboard, XSIAMReport]


class ValidateXsaimContentPathValidator(BaseValidator[ContentTypes]):
    error_code = "XD100"
    description = ""
    rationale = ""
    error_message = ""
    fix_message = ""
    related_field = ""
    is_auto_fixable = True

    
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
            

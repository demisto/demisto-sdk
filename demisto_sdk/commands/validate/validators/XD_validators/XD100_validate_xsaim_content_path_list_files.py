
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.content_graph.objects.xsiam_dashboard import XSIAMDashboard
from demisto_sdk.commands.content_graph.objects.xsiam_report import XSIAMReport

from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

from demisto_sdk.commands.validate.validators.XD_validators.XD100_validate_xsaim_content_path import ValidateXsaimContentPathValidator

ContentTypes = Union[ModelingRule, ParsingRule, CorrelationRule, XSIAMDashboard, XSIAMReport]


class ValidateXsaimContentPathValidatorListFiles(ValidateXsaimContentPathValidator, BaseValidator[ContentTypes]):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return self.obtain_invalid_content_items_using_graph(content_items, False)
        
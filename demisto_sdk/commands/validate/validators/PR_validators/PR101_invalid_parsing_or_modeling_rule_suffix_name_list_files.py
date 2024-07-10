
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule

from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

from demisto_sdk.commands.validate.validators.PR_validators.PR101_invalid_parsing_or_modeling_rule_suffix_name import ParsingAndModelingRuleSuffixNameValidator

ContentTypes = Union[ModelingRule, ParsingRule]


class ParsingAndModelingRuleSuffixNameValidatorListFiles(ParsingAndModelingRuleSuffixNameValidator, BaseValidator[ContentTypes]):
    expected_execution_mode = [ExecutionMode.ALL_FILES]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return self.is_valid_using_graph(content_items, False)
        
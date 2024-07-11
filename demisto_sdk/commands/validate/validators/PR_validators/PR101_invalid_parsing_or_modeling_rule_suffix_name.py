
from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    MODELING_RULE,
    MODELING_RULE_ID_SUFFIX,
    MODELING_RULE_NAME_SUFFIX,
    PARSING_RULE,
    PARSING_RULE_ID_SUFFIX,
    PARSING_RULE_NAME_SUFFIX,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
)
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[ModelingRule, ParsingRule]

class ParsingAndModelingRuleSuffixNameValidator(BaseValidator[ContentTypes]):
    error_code = "PR101"
    description = ""
    rationale = ""
    error_message = "The file {} is invalid, the rule id should end with {} and rule name should end with {}"
    related_field = "object_id, name"
    is_auto_fixable = False

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.path, content_item.object_id, content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                (content_item.content_type == ContentType.MODELING_RULE and not content_item.name.endswith(MODELING_RULE_NAME_SUFFIX)) or
                (content_item.content_type == ContentType.MODELING_RULE and not content_item.object_id.endswith(MODELING_RULE_ID_SUFFIX)) or
                (content_item.content_type == ContentType.PARSING_RULE and not content_item.name.endswith(PARSING_RULE_NAME_SUFFIX)) or
                (content_item.content_type == ContentType.PARSING_RULE and not content_item.object_id.endswith(PARSING_RULE_ID_SUFFIX))
            )
        ]
        

    

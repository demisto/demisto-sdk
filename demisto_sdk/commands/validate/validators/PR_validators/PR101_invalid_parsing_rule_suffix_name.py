from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    PARSING_RULE_ID_SUFFIX,
    PARSING_RULE_NAME_SUFFIX,
)
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ParsingRule


class ParsingRuleSuffixNameValidator(BaseValidator[ContentTypes]):
    error_code = "PR101"
    description = ""
    rationale = ""
    error_message = "The file {} is invalid, the parsing rule id should end with {} and rule name should end with {}"
    related_field = "id, name"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.path, content_item.object_id, content_item.name
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                (
                    not content_item.name.endswith(PARSING_RULE_NAME_SUFFIX)
                )
                or (
                    not content_item.object_id.endswith(PARSING_RULE_ID_SUFFIX)
                )
            )
        ]

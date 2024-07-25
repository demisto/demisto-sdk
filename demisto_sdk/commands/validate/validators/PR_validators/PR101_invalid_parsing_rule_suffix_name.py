from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    PARSING_RULE_ID_SUFFIX,
    PARSING_RULE_NAME_SUFFIX,
)
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ParsingRule


class ParsingRuleSuffixNameValidator(BaseValidator[ContentTypes]):
    error_code = "PR101"
    description = (
        "Checks that id and name in the parsing rule, end with the correct suffixes."
    )
    rationale = "To prevent confusion caused by ambiguous naming of modeling and parsing rules in XSIAM UI, the validation ensures the rule ID and name end with 'ParsingRule' or 'Parsing Rule'. This will help avoid naming conflicts and improve clarity in release notes."
    error_message = "The file {} is invalid, the parsing rule id {} should end with {} and rule name {} should end with {}"
    related_field = "id, name"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.path,
                    content_item.object_id,
                    PARSING_RULE_ID_SUFFIX,
                    content_item.name,
                    PARSING_RULE_NAME_SUFFIX,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                (not content_item.name.endswith(PARSING_RULE_NAME_SUFFIX))
                or (not content_item.object_id.endswith(PARSING_RULE_ID_SUFFIX))
            )
        ]

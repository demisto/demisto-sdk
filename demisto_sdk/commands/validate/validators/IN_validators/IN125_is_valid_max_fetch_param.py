from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import DEFAULT_MAX_FETCH, MAX_FETCH
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.tools import find_param
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidMaxFetchParamValidator(BaseValidator[ContentTypes]):
    error_code = "IN125"
    description = "Validate that the max_fetch param has a defaultvalue"
    rationale = (
        "To maintain optimal load in the platform, the maximal number of incidents per fetch is limited. "
        "For more details, see https://xsoar.pan.dev/docs/integrations/fetching-incidents#fetch-limit"
    )
    error_message = "The integration is a fetch integration with max_fetch param, please make sure the max_fetch param has a default value."
    fix_message = (
        f"Added a 'defaultvalue = {DEFAULT_MAX_FETCH}' to the max_fetch param."
    )
    related_field = "defaultvalue"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_fetch
            and (max_fetch_param := find_param(content_item.params, MAX_FETCH))
            and not max_fetch_param.defaultvalue
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        max_fetch_param = find_param(content_item.params, MAX_FETCH)
        if max_fetch_param:
            max_fetch_param.defaultvalue = DEFAULT_MAX_FETCH
        return FixResult(
            validator=self,
            message=self.fix_message.format(),
            content_object=content_item,
        )

from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import SUPPORTED_CONTRIBUTORS_LIST
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsURLOrEmailExistsValidator(BaseValidator[ContentTypes]):
    error_code = "PA113"
    description = "Validate that a partner/developer pack has at least an email or a url address fields filled."
    rationale = "Packs with Partner or developer support levels require a contact method (email or URL) for user support and information."
    error_message = "The pack must include either an email or an URL addresses."
    related_field = "url, email."
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.support in SUPPORTED_CONTRIBUTORS_LIST
            and not content_item.url
            and not content_item.email
        ]

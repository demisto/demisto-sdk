from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import SUPPORTED_CONTRIBUTORS_LIST
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsValidURLFieldValidator(BaseValidator[ContentTypes]):
    error_code = "PA127"
    description = "Validate that the pack metadata contains a valid URL field."
    rationale = (
        "URLs help users access support or report issues for the pack directly. "
        "For more info, see: https://xsoar.pan.dev/docs/packs/packs-format#pack_metadatajson"
    )
    error_message = "The metadata URL leads to a GitHub repo instead of a support page. Please provide a URL for a support page as detailed in:\nhttps://xsoar.pan.dev/docs/packs/packs-format#pack_metadatajson\nNote that GitHub URLs that lead to a /issues page are also acceptable. (e.g. https://github.com/some_monitored_repo/issues)"
    related_field = "url"
    fix_message = "Fixed the URL to include the issues endpoint. URL is now: {0}."
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.support in SUPPORTED_CONTRIBUTORS_LIST
            and content_item.url
            and (metadata_url := content_item.url.lower().strip())
            and len(re.findall("github.com", metadata_url)) > 0
            and not metadata_url.endswith("/issues")
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.url = f"{content_item.url}/issues"
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.url),
            content_object=content_item,
        )

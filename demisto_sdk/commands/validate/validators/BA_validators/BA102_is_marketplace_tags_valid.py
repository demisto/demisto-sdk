
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    MARKETPLACE_LIST_PATTERN,
    VALID_MARKETPLACE_TAGS,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ContentTypes,
    ValidationResult,
)


class MarketplaceTagsValidator(BaseValidator[ContentTypes], ABC):
    error_code = "BA102"
    description = (
        "Ensures that all marketplace tags (e.g. <~xsiam></~xsiam>) are valid, "
        "properly matched, and not nested incorrectly."
    )
    rationale = (
        "Incorrect tags (invalid names, mismatched opening/closing tags, or improper nesting) "
        "can lead to incorrect display or filtering in the Marketplace. "
    )
    error_message = "Invalid or malformed marketplace tags detected: {}"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.README, RelatedFileType.DESCRIPTION_File, RelatedFileType.RELEASE_NOTE]


    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_tags)),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_tags := self.check_tags(self.get_relevant_file_content(content_item)))
        ]

    @abstractmethod
    def get_relevant_file_content(self, content_item) -> str:
        """Extract the relevant file content from the content item for tag validation."""
        pass

    def check_tags(self, text: str) -> str | None:
        """
        Checks for unmatched, mismatched, or improperly nested <~...> and </~...> tags.
        Returns an error message if there’s an issue, or None if all tags are matched correctly.
        """
        tag_pattern = re.compile(rf"<(?P<closing>/)?~(?P<name>{MARKETPLACE_LIST_PATTERN})>")
        stack = []

        for match in tag_pattern.finditer(text):
            tag_name = match.group("name")
            is_closing = bool(match.group("closing"))

            invalid_tags = [tag for tag in tag_name.split(',') if tag not in VALID_MARKETPLACE_TAGS]
            if invalid_tags:
                return f"Invalid marketplace tag(s): {', '.join(invalid_tags)}"

            if not is_closing:
                if stack:
                    return f"Nested tag error: <~{tag_name}> found inside <~{stack[-1]}>"
                stack.append(tag_name)

            else:
                if not stack:
                    return f"Unexpected closing tag: </~{tag_name}> with no matching opening tag"
                last_opened = stack.pop()
                if last_opened != tag_name:
                    return f"Mismatched tag: expected </~{last_opened}>, but found </~{tag_name}>"

        if stack:
            return f"Unclosed tag: <~{stack[-1]}> has no matching closing tag"

        return None

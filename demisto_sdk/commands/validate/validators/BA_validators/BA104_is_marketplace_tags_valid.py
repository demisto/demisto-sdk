from __future__ import annotations

import re
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    MARKETPLACE_LIST_PATTERN,
    VALID_MARKETPLACE_TAGS,
)
from demisto_sdk.commands.common.tools import get_relative_path_from_packs_dir
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Pack, Integration]


class MarketplaceTagsValidator(BaseValidator[ContentTypes]):
    error_code = "BA104"
    description = (
        "Ensures that all marketplace tags (e.g. <~xsiam></~xsiam>) are valid, "
        "properly matched, and not nested incorrectly."
    )
    rationale = (
        "Incorrect tags (invalid names, mismatched opening/closing tags, or improper nesting) "
        "can lead to incorrect display or filtering in the Marketplace. "
    )
    error_message = "Found malformed marketplace tags in the following files:\n{}"
    is_auto_fixable = False
    related_file_type = [
        RelatedFileType.README,
        RelatedFileType.DESCRIPTION_File,
        RelatedFileType.RELEASE_NOTE,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_tags)),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_tags := self.validate_content_item_files(content_item))
        ]

    def validate_content_item_files(self, content_item: ContentTypes) -> List[str]:
        """Validate marketplace tags in content item files.

        Args:
            content_item: The content item to validate (Pack or Integration)

        Returns:
            List of error messages for invalid tags found
        """
        error_messages = []
        files_to_check = []

        if isinstance(content_item, Pack):
            files_to_check.extend([content_item.readme, content_item.release_note])
        elif isinstance(content_item, Integration):
            files_to_check.append(content_item.description_file)

        for file in files_to_check:
            if file and (error := self.check_tags_in_text(file.file_content)):
                pack_path = get_relative_path_from_packs_dir(str(file.file_path))
                error_messages.append(f"{pack_path}: {error}")

        return error_messages

    def check_tags_in_text(self, text: str) -> str | None:
        """
        Checks for unmatched, mismatched, or improperly nested <~...> and </~...> tags.
        Returns an error message if there’s an issue, or None if all tags are matched correctly.
        """
        tag_pattern = re.compile(
            rf"<(?P<closing>/)?~(?P<name>{MARKETPLACE_LIST_PATTERN})>"
        )
        stack: List[str] = []

        for match in tag_pattern.finditer(text):
            tag_name = match.group("name")
            is_closing = bool(match.group("closing"))

            invalid_tags = [
                tag for tag in tag_name.split(",") if tag not in VALID_MARKETPLACE_TAGS
            ]
            if invalid_tags:
                return f"Invalid marketplace tag(s) found: {', '.join(invalid_tags)}. Allowed tags: {', '.join(VALID_MARKETPLACE_TAGS)}"

            if not is_closing:
                if stack:
                    return f"Nested marketplace tags are not allowed. Tag '{tag_name}' cannot be placed inside tag '{stack[-1]}'"
                stack.append(tag_name)

            else:
                if not stack:
                    return f"Closing tag '{tag_name}' found without corresponding opening tag"
                last_opened = stack.pop()
                if last_opened != tag_name:
                    return f"Mismatched marketplace tags: opened with '{last_opened}' but closed with '{tag_name}'"

        if stack:
            return f"Unclosed marketplace tag: '{stack[-1]}' is missing its closing tag"

        return None

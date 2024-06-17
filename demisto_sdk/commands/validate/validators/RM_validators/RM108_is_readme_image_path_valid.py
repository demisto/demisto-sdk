from __future__ import annotations

from typing import Union

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM108_is_image_path_valid import (
    RelativeImagePathValidator,
)

ContentTypes = Union[Script, Playbook, Pack]


class ReadmeRelativeImagePathValidator(
    RelativeImagePathValidator, BaseValidator[ContentTypes]
):
    related_file_type = [RelatedFileType.README]

    def validate_content_items(self, content_item: ContentTypes) -> str:
        """Check if the content items are valid.

        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            str -- The error message if the content item isn't valid.
        """
        error_message = self.detect_absolute_image_paths(
            content_item.readme.file_content
        ) + self.verify_relative_saved_in_doc_files(content_item.readme.file_content)
        return error_message

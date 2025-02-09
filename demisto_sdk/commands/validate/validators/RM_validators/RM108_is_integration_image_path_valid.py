from __future__ import annotations

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.RM_validators.RM108_is_image_path_valid import (
    RelativeImagePathValidator,
)

ContentTypes = Integration


class IntegrationRelativeImagePathValidator(RelativeImagePathValidator[ContentTypes]):
    related_file_type = [RelatedFileType.README, RelatedFileType.DESCRIPTION_File]

    def validate_content_items(self, content_item: ContentTypes) -> dict:
        """Check if the content items are valid by passing verify_absolute_images_not_exist and verify_relative_saved_in_doc_files.

        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            dict -- The error message for each related file mapped by related file path.
        """
        return {
            str(content_item.readme.file_path): self.detect_absolute_image_paths(
                content_item.readme.file_content
            )
            + self.verify_relative_saved_in_doc_files(content_item.readme.file_content),
            str(
                content_item.description_file.file_path
            ): self.detect_absolute_image_paths(
                content_item.description_file.file_content
            )
            + self.verify_relative_saved_in_doc_files(
                content_item.description_file.file_content
            ),
        }

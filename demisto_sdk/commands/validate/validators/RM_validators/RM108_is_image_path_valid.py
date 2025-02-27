from __future__ import annotations

import re
from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    DOC_FILE_IMAGE_REGEX,
    HTML_IMAGE_LINK_REGEX,
    URL_IMAGE_LINK_REGEX,
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ContentTypes,
    ValidationResult,
)


class RelativeImagePathValidator(BaseValidator[ContentTypes], ABC):
    error_code = "RM108"
    description = (
        "This validation verifies that images in the readme and description files are"
        " relative and stored in doc_files."
    )
    rationale = (
        "Using relative references to files in the repo folder enhances security by reducing reliance"
        " on external links, minimizing the risk of link manipulation or redirection attacks. "
    )
    error_message = (
        "{} Read the following documentation on how to add images to pack markdown files:\n"
        " https://xsoar.pan.dev/docs/integrations/integration-docs#images"
    )
    related_file_type = [RelatedFileType.README, RelatedFileType.DESCRIPTION_File]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results: List[ValidationResult] = []
        for content_item in content_items:
            if invalid_md_files := self.validate_content_items(content_item):
                for file_path, error_message in invalid_md_files.items():
                    if error_message:
                        validation_results.append(
                            ValidationResult(
                                validator=self,
                                message=self.error_message.format(error_message),
                                content_object=content_item,
                                path=file_path,
                            )
                        )
        return validation_results

    def validate_content_items(self, content_item):
        """Check if the content items are valid by passing verify_absolute_images_not_exist and verify_relative_saved_in_doc_files.

        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            dict -- The error message for each related file mapped by related file path.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def detect_absolute_image_paths(self, content_item) -> str:
        """Check if the content item contains absolute image paths.

        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            str -- The error message if the content item contains absolute paths.
        """
        absolute_links = re.findall(
            URL_IMAGE_LINK_REGEX + r"|" + HTML_IMAGE_LINK_REGEX,
            content_item,
            re.IGNORECASE | re.MULTILINE,
        )
        if absolute_links:
            # Extract and filter links in a single pass
            absolute_links_without_assets = []

            for absolute_link in absolute_links:
                # Choose the appropriate link
                link = absolute_link[1] if absolute_link[0] else absolute_link[2]

                # Skip links that contain "content-assets" and end with ".gif"
                if link and not ("content-assets" in link and link.endswith(".gif")):
                    absolute_links_without_assets.append(link)

            if absolute_links_without_assets:
                return (
                    " Invalid image path(s) have been detected."
                    " Please utilize relative paths instead for the links provided below:\n"
                    + "\n".join(absolute_links_without_assets)
                    + "\n\n"
                )
        return ""

    def verify_relative_saved_in_doc_files(self, content_item) -> str:
        """Check if the content item contains exists image paths.

        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            str -- The error message if the content item contains relative images that are not saved in the
             pack's doc_files folder.
        """
        relative_images = re.findall(
            r"(\!\[.*?\])\(((?!http).*?)\)$"
            + r"|"
            + r'(<img.*?src\s*=\s*"((?!http).*?)")',
            content_item,
            re.IGNORECASE | re.MULTILINE,
        )
        relative_images = [
            # extracts the actual image path from each matched link tuple in the relative_images list.
            # It selects between relative_image[1] and relative_image[2] based on whether the link
            # matches the URL or HTML pattern.
            relative_image[1] if relative_image[0] else relative_image[2]
            for relative_image in relative_images
        ]
        invalid_links = [
            rel_img
            for rel_img in relative_images
            if not re.search(DOC_FILE_IMAGE_REGEX, rel_img)
        ]
        if invalid_links:
            return (
                "Relative image paths have been identified outside the pack's 'doc_files' directory. Please relocate"
                " the following images to the 'doc_files' directory:\n"
                + "\n".join(invalid_links)
                + "\n\n"
            )
        return ""

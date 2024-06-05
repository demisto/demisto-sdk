from __future__ import annotations

import re
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import (
    DOC_FILE_IMAGE_REGEX,
    HTML_IMAGE_LINK_REGEX,
    URL_IMAGE_LINK_REGEX,
    GitStatuses,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook, Pack]


class ReadmeDescriptionImageValidator(BaseValidator[ContentTypes]):
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
        "{}. See https://xsoar.pan.dev/docs/integrations/integration-docs#images for further info on"
        " how to add images to pack markdown files."
    )
    related_file_type = [RelatedFileType.README, RelatedFileType.DESCRIPTION_File]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(error_message),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                error_message := self.verify_absolute_images_not_exist(
                    content_item.readme.file_content
                )
                + self.verify_relative_saved_in_doc_files(
                    content_item.readme.file_content
                )
                + self.verify_absolute_images_not_exist(content_item.description_file.file_content)
                + self.verify_relative_saved_in_doc_files(content_item.description_file.file_content)
            )
        ]

    def verify_absolute_images_not_exist(self, content_item) -> str:
        """Check if the content item contains exists image paths.


        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            str -- The error message if the content item contains absolute paths.
        """
        matches = re.findall(
            URL_IMAGE_LINK_REGEX + r"|" + HTML_IMAGE_LINK_REGEX,
            content_item,
            re.IGNORECASE | re.MULTILINE,
        )
        if matches:
            absolute_links = " \n".join(
                match[1] if match[0] else match[2] for match in matches
            )
            return f"Invalid image path(s), use relative paths instead in the following links:\n{absolute_links}.\n"
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
            match[1] if match[0] else match[2] for match in relative_images
        ]
        invalid_links = [
            rel_img
            for rel_img in relative_images
            if not re.match(DOC_FILE_IMAGE_REGEX, rel_img)
        ]
        if invalid_links:
            return (
                "Relative image paths found not in pack's doc_files. Please move the following to doc_file:\n"
                + "\n".join(invalid_links)
            )
        return ""

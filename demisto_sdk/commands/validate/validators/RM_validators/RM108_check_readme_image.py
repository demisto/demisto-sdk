
from __future__ import annotations

from typing import Iterable, List, Union
from pathlib import Path
from urllib.parse import urlparse
import requests
import re

from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)
from demisto_sdk.commands.common.constants import (
    HTML_IMAGE_LINK_REGEX,
    URL_IMAGE_LINK_REGEX,
    DOC_FILE_IMAGE_REGEX
)

from demisto_sdk.commands.common.tools import (
    extract_image_paths_from_str,
    get_full_image_paths_from_relative,
    get_pack_name,
)


ContentTypes = Union[Integration, Script, Playbook, Pack]


class CheckReadmeImageValidator(BaseValidator[ContentTypes]):
    error_code = "RM108"
    description = "This validation checks that the image in the readme file is relative."
    rationale = "Using relative references to files in the repo folder enhances security by reducing reliance on external links, minimizing the risk of link manipulation or redirection attacks. "
    error_message = "{}. See https://xsoar.pan.dev/docs/integrations/integration-docs#images for further info on how to add images to pack markdown files."
    related_field = "readme, description"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.README, RelatedFileType.DESCRIPTION_File]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(error_message)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                error_message := self.verify_absolute_images_not_exist(content_item.description) +
                                 self.verify_relative_saved_in_doc_files(content_item.description) +
                                 self.verify_absolute_images_not_exist(content_item.readme.file_content) +
                                 self.verify_relative_saved_in_doc_files(content_item.readme.file_content)
            )
        ]


    def verify_absolute_images_not_exist(self, content_item: str) -> str:
        """Check if the content item contains exists image paths.
        
        
        Arguments:
            content_item {ContentTypes} -- The content item to check.

        Returns:
            str -- The error message if the content item contains absolute paths.
        """
        if not content_item:
            return ""
        error_message = ""
        absolute_links = re.findall(
                URL_IMAGE_LINK_REGEX,
                content_item,
                re.IGNORECASE | re.MULTILINE,
            )
        absolute_links += re.findall(
            HTML_IMAGE_LINK_REGEX,
            content_item,
            re.IGNORECASE | re.MULTILINE,
        )
        if absolute_links:
            error_message = f"Detected the following invalid image path:{absolute_links}. Absolute paths are not supported in pack README files. Please use relative paths instead. \n"

        return error_message
    
    
    def verify_relative_saved_in_doc_files(self, content_item: str) -> str:
            """Check if the content item contains exists image paths.
            
            
            Arguments:
                content_item {ContentTypes} -- The content item to check.

            Returns:
                str -- The error message if the content item contains relative images that are not saved in the pack's doc_files folder.
            """
            if not content_item:
                return ""
            error_message = ""
            relative_images = re.findall(
                r"(\!\[.*?\])\(((?!http).*?)\)$",
                content_item,
                re.IGNORECASE | re.MULTILINE,
            )
            relative_images += re.findall(  # HTML image tag
                r'(<img.*?src\s*=\s*"((?!http).*?)")',
                content_item,
                re.IGNORECASE | re.MULTILINE,
            )
            if relative_images:
                invalid_links = [relative_image_path for relative_image_path in relative_images if not re.match(DOC_FILE_IMAGE_REGEX, relative_image_path)]
                if invalid_links:
                    error_message += f"Detected that the relative image paths are not in the pack's doc_files:{invalid_links}. Please move them to the pack's doc_files folder."
            return error_message

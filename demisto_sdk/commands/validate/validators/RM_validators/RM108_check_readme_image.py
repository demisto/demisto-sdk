
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
                error_message := self.verify_absolute_images_not_exist(content_item.description_file) +
                                 self.verify_relative_saved_in_doc_files(content_item.description_file) +
                                 self.verify_absolute_images_not_exist(content_item.readme.file_content) +
                                 self.verify_relative_saved_in_doc_files(content_item.readme.file_content)
            )
        ]


    def verify_absolute_images_not_exist(self, content_item: str) -> str:
        """Check for existing absolute image paths."""
        error_message = ""
        absolute_links = re.findall(URL_IMAGE_LINK_REGEX + r'|' + HTML_IMAGE_LINK_REGEX, content_item, re.IGNORECASE | re.MULTILINE)
        if absolute_links:
            error_message = f"Invalid image path(s): {absolute_links}. Use relative paths instead.\n"
        return error_message
        
        
    def verify_relative_saved_in_doc_files(self, content_item: str) -> str:
        """Check for relative image paths not saved in the pack's doc_files folder."""
        if not content_item:
            return ""
        error_message = ""
        relative_images = re.findall(r"(\!\[.*?\])\(((?!http).*?)\)$" +
                                    r'|' + r'(<img.*?src\s*=\s*"((?!http).*?)")',
                                    content_item,
                                    re.IGNORECASE | re.MULTILINE)
        invalid_links = [rel_img for rel_img in relative_images if not re.match(DOC_FILE_IMAGE_REGEX, rel_img)]
        if invalid_links:
            error_message += f"Relative image paths not in pack's doc_files:{invalid_links}. Move them to the folder."
        return error_message

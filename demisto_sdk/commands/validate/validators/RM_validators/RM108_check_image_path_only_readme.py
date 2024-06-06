from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.RM_validators.RM108_check_image_path import (
    ImagePathValidator,
)

ContentTypes = Union[Script, Playbook, Pack]


class ImagePathOnlyReadMeValidator(ImagePathValidator, BaseValidator[ContentTypes]):
    related_file_type = [RelatedFileType.README]

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
            )
        ]

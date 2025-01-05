from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Playbook


class MissingPlaybookImageValidator(BaseValidator[ContentTypes]):
    error_code = "RM116"
    description = "Verifies that a playbook image exists in the doc_files folder"
    rationale = "It is recommended to have an image for every playbook for better understanding and documentation"
    error_message = "Couldn't find a playbook image in the doc_files folder for the playbook file {playbook_file_name}, The image should be a png file with the playbook's file name without the playbook prefix."
    related_field = ""
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    playbook_file_name=content_item.path.stem
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                (
                    not content_item.image.exist
                    or "doc_files" not in str(content_item.image.file_path)
                )
                and not content_item.is_silent
            )
        ]

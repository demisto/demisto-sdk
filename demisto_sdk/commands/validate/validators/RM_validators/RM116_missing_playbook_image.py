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
    rationale = "It is recommended to have an image for every playbook for better understanding and documentation."
    error_message = "Couldn't find an image for the playbook under doc_files, please make sure the playbook has an image and that it is located under the pack's doc_files folder."
    related_field = "image"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                not content_item.image.exist
                or "doc_files" not in str(content_item.image.file_path)
            )
        ]

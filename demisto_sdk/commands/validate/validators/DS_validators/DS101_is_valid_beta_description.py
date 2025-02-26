from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    BETA_INTEGRATION_DISCLAIMER,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidBetaDescriptionValidator(BaseValidator[ContentTypes]):
    error_code = "DS101"
    description = "Check if beta disclaimer exists in detailed description"
    rationale = "Need a disclaimer for beta integrations."
    error_message = (
        f"No beta disclaimer note was found. "
        f"Please make sure the description file (integration_name_description.md)"
        f" includes the beta disclaimer note. "
        f"Add the following to the detailed description:\n{BETA_INTEGRATION_DISCLAIMER}"
    )
    related_field = "beta"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.DESCRIPTION_File]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
                path=content_item.description_file.file_path,
            )
            for content_item in content_items
            if content_item.is_beta
            and BETA_INTEGRATION_DISCLAIMER
            not in content_item.description_file.file_content
        ]

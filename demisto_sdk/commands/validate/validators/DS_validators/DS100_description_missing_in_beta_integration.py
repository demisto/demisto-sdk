from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class DescriptionMissingInBetaIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "DS100"
    description = "Check whether a description file exists for a beta integration."
    rationale = "Need a disclaimer for beta integrations."
    error_message = "Beta integration needs a description."
    related_field = "beta"
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
            if content_item.is_beta and not content_item.description_file.exist
        ]

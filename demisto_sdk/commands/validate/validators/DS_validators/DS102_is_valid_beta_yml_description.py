
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
        GitStatuses,
        BETA_INTEGRATION_DISCLAIMER
)
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Integration


class IsValidBetaYmlDescriptionValidator(BaseValidator[ContentTypes]):
    error_code = "DS102"
    description = "Check if beta disclaimer exists in yml detailed description"
    rationale = "Need a disclaimer for beta integrations in the description."
    error_message = f"The detailed description field in beta integration does not contain the beta disclaimer note. Add the following to the detailed description:\n {BETA_INTEGRATION_DISCLAIMER}"
    related_field = "beta"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_beta and BETA_INTEGRATION_DISCLAIMER not in content_item.description
        ]
    

    


from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        FixResult,
        ValidationResult,
)

ContentTypes = Integration


class IsValidAsMappableIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN131"
    description = "Validate that the integration is valid as a mappable integration."
    error_message = "The integration is a mappable integration and is missing the 'get-mapping-fields' command. Please add the command."
    fix_message = "Added the 'get-mapping-fields' command to the integration."
    related_field = "ismappable, commands"
    is_auto_fixable = True

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        # Add your validation right here
        pass
    

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        pass
            

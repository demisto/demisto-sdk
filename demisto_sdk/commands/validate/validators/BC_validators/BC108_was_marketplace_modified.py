
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        FixResult,
        ValidationResult,
)

ContentTypes = Union[Integration, Script, IncidentType, Mapper, IndicatorField, IndicatorType, IncidentField]


class WasMarketplaceModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC108"
    description = "Ensuring that the "marketplaces" property hasn't been newly added (if it didn't exist before) or that its values haven't been removed."
    error_message = "You can't add or remove the 'marketplaces' field from existing content. Undo it or ask for a force merge."
    fix_message = ""
    related_field = ""
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.MODIFIED]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                # Add your validation right here
            )
        ]
    

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        pass
            

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
from demisto_sdk.commands.content_graph.objects import Pack
from demisto_sdk.commands.content_graph.objects import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[
    Integration,
    Script,
    IncidentType,
    Mapper,
    IndicatorField,
    IndicatorType,
    IncidentField,
    Pack,
    Playbook
]


class WasMarketplaceModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC108"
    description = "Ensuring that the 'marketplaces' property hasn't been newly added (if it didn't exist before) or that its values haven't been removed."
    error_message = "You can't add or remove the 'marketplaces' field from existing content. Undo it or ask for a force merge."
    fix_message = ""
    related_field = ""
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.MODIFIED]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:

            new_marketplaces = content_item.marketplaces
            old_marketplaces = content_item.old_base_content_object.marketplaces
            
            # if the content is not a pack, we may want to compare to the pack marketplaces as well, since it inherits the pack marketplaces, if not specified
            if not isinstance(content_item, Pack):
                pack_marketplaces = content_item.in_pack.marketplaces
                
                # If all four marketplaces are included, it might be due to the field appearing empty. However, in reality, it did contain a specific marketplace inherited from the pack. 
                # In this scenario, we will compare the pack's marketplaces as it serves as the source of truth.
                if len (old_marketplaces) == 4:
                    old_marketplaces = pack_marketplaces

            if not (set(old_marketplaces).issubset(set(new_marketplaces))):
                results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message,
                            content_object=content_item,
                        )
                    )

        return results
        
    

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        pass

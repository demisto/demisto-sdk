from __future__ import annotations

from typing import Iterable, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[IncidentField, IndicatorField]
from demisto_sdk.commands.common.constants import MarketplaceVersions

class IsAliasInnerAliasValidator(BaseValidator[ContentTypes]):
    error_code = "IF117"
    description = "Checks if marketplace value in aliases is valid."
    rationale = "marketplace in aliases should be ['xsoar']."
    error_message = ('The following fields exist as aliases and have invalid "marketplaces" key value: \n{0}\n '
                     'the value of the "marketplaces" key in these fields should be ["xsoar"].')
    related_field = "Aliases"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> list[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(aliases=", ".join(aliases)),
                content_object=content_item,
            )
            for content_item in content_items
            if (aliases := invalid_aliases_marketplace(content_item.data.get("Aliases", [])))
        ]


def invalid_aliases_marketplace(aliases: list[dict]) -> list[str]:
    """Checks if the marketplace of the aliases is valid.
    Args:
        aliases (list[dict]): The list of alias objects.
    Returns:
        list[str]: A list of the names of aliases that have invalid marketplace.
    """

    return [
        str(alias.get("cliName") or alias.get("cliname"))
        for alias in aliases
        if alias.get('marketplaces') != [MarketplaceVersions.XSOAR.value]
    ]

from __future__ import annotations

from typing import Iterable, Union

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    OLDEST_INCIDENT_FIELD_SUPPORTED_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[IncidentField, IndicatorField]


class IsValidAliasMarketplaceValidator(BaseValidator[ContentTypes]):
    error_code = "IF117"
    description = "Checks if marketplace value in aliases is valid."
    rationale = "marketplace in aliases should be ['xsoar']."
    error_message = (
        "The following fields exist as aliases and have invalid 'marketplaces' key value: \n{aliases}\n "
        "the value of the 'marketplaces' key in these fields should be ['xsoar']."
    )
    related_field = "Aliases"

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
            if (aliases := self.invalid_aliases_marketplace(content_item))
        ]

    def invalid_aliases_marketplace(self, content_item):
        """Checks if the marketplace of the aliases is valid.
        Args:
            content_item : The content item.
        Returns:
            list[str]: A list of the names of aliases that have invalid marketplace.
        """
        invalid_aliases = []
        aliases = content_item.data.get("Aliases", [])

        if aliases:
            incident_fields = self._get_incident_fields_by_aliases(aliases)
            for item in incident_fields:
                alias_marketplaces = item.marketplaces
                alias_toversion = Version(item.toversion)

                if alias_toversion > Version(
                    OLDEST_INCIDENT_FIELD_SUPPORTED_VERSION
                ) and (
                    len(alias_marketplaces) > 2  # marketplaces are xsoar and xsoar.saas
                    or alias_marketplaces[0] != MarketplaceVersions.XSOAR.value
                ):
                    invalid_aliases.append(item.cli_name)
        return invalid_aliases

    def _get_incident_fields_by_aliases(self, aliases: list[dict]) -> list:
        """
        Get from the graph the actual fields for the given aliases

        Args:
            aliases (list): The alias list.

        Returns:
            list: A list of dictionaries, each dictionary represent an incident field.
        """
        alias_ids: set = {f'{alias.get("cliName")}' for alias in aliases}
        return self.graph.search(
            cli_name=alias_ids,
            content_type=ContentType.INCIDENT_FIELD,
        )

from typing import Set, Tuple

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)


class Playbook(ContentItem, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    def metadata_fields(self) -> Set[str]:
        return {"name", "description"}

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace, **kwargs)
        script_names = self.get_script_names_from_playbooks_intended_preparation()
        return MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
            data,
            script_names,
            current_marketplace=current_marketplace,
            supported_marketplaces=self.marketplaces,
        )

    def get_script_names_from_playbooks_intended_preparation(self) -> Tuple[str, ...]:
        return tuple(
            map(
                lambda s: s.object_id,
                filter(
                    lambda s: (
                        isinstance(s, Script)
                        and s.is_incident_to_alert(MarketplaceVersions.MarketplaceV2)
                    ),
                    tuple(
                        map(
                            lambda content_item: content_item.content_item_to, self.uses
                        )
                    ),
                ),
            )
        )

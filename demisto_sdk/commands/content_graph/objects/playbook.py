from typing import Callable, Optional

import demisto_client

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)


class Playbook(ContentItem, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        # taking the description from the data after preparing the playbook to upload
        # this might be different when replacing incident to alert in the description for marketplacev2
        summary["description"] = self.data.get("description") or ""
        return summary

    def prepare_for_upload(
        self,
        current_marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs
    ) -> dict:
        data = super().prepare_for_upload(current_marketplace, **kwargs)
        return MarketplaceIncidentToAlertPlaybooksPreparer.prepare(
            self,
            data,
            current_marketplace=current_marketplace,
            supported_marketplaces=self.marketplaces,
        )

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_playbook

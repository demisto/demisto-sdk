from typing import Callable, Dict, Optional

import demisto_client

from demisto_sdk.commands.common.constants import (
    PACKS_README_FILE_NAME,
    MarketplaceVersions,
    RelatedFileType,
)
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.prepare_content.preparers.marketplace_incident_to_alert_playbooks_prepare import (
    MarketplaceIncidentToAlertPlaybooksPreparer,
)


class BasePlaybook(ContentItem, content_type=ContentType.PLAYBOOK):  # type: ignore[call-arg]
    version: Optional[int] = 0

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
        **kwargs,
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

    def get_related_content(self) -> Dict[RelatedFileType, Dict]:
        related_content_files = super().get_related_content()
        related_content_files.update(
            {
                RelatedFileType.IMAGE: {
                    "path": [
                        str(
                            self.path.parents[1]
                            / "doc_files"
                            / str(self.path.parts[-1])
                            .replace(".yml", ".png")
                            .replace("playbook-", "")
                        ),
                        str(self.path).replace(".yml", ".png"),
                    ],
                    "git_status": None,
                },
                RelatedFileType.README: {
                    "path": [
                        str(
                            self.path.parent
                            / str(self.path.parts[-1]).replace(
                                ".yml", f"_{PACKS_README_FILE_NAME}"
                            )
                        )
                    ],
                    "git_status": None,
                },
            }
        )
        return related_content_files

    @property
    def readme(self) -> str:
        return self.get_related_text_file(RelatedFileType.README)

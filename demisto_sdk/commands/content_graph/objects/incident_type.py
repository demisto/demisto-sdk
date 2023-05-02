from typing import Callable, Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentType(ContentItem, content_type=ContentType.INCIDENT_TYPE):  # type: ignore[call-arg]
    playbook: Optional[str]
    hours: int
    days: int
    weeks: int
    closure_script: Optional[str] = Field(alias="closureScript")

    def metadata_fields(self) -> Set[str]:
        return {"name", "playbook", "closure_script", "hours", "days", "week"}

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
        dump_into_list: bool = False,
    ) -> None:
        # sets dump_into_list = True
        return super()._upload(client, marketplace, dump_into_list=True)

    @classmethod
    def _client_upload_method(cls, client: demisto_client) -> Callable:
        return client.import_incident_types_handler

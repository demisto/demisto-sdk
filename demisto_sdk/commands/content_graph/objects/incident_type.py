from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Set

import demisto_client
from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

json = JSON_Handler()


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
    ) -> None:
        with TemporaryDirectory() as dir:
            file_path = Path(dir, self.normalize_name)
            with open(file_path, "w") as f:
                # Wrapping the dictionary with a list, as that's what the server expects
                json.dump([self.prepare_for_upload(marketplace=marketplace)], f)
            client.import_incident_types_handler(str(file_path))

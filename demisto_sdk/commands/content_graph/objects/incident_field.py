import platform
from tempfile import NamedTemporaryFile
from typing import Optional, Set

import demisto_client
from pydantic import Field
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

json = JSON_Handler()


class IncidentField(ContentItem, content_type=ContentType.INCIDENT_FIELD):  # type: ignore[call-arg]
    cli_name: str = Field(alias="cliName")
    field_type: str = Field(alias="type")
    associated_to_all: bool = Field(False, alias="associatedToAll")

    def summary(
        self,
        marketplace: Optional[MarketplaceVersions] = None,
        incident_to_alert: bool = False,
    ) -> dict:
        summary = super().summary(marketplace, incident_to_alert)
        summary["id"] = f"incident_{self.object_id}"
        return summary

    def metadata_fields(self) -> Set[str]:
        return super().metadata_fields().union({"field_type"})

    def _upload(
        self,
        client: demisto_client,
        marketplace: MarketplaceVersions,
    ) -> None:
        is_win_os = platform.system() == "Windows"

        # Set delete to False if a Windows operating system is detected
        # On Windows operating systems, NamedTemporaryFile objects cannot be
        # opened a second time while open in a context manager
        with NamedTemporaryFile(
            suffix=".json",
            mode="r+",
            delete=not is_win_os,
        ) as file:
            json.dump(
                # Wrapping the data as the server expects to receive it
                {"incidentFields": [self.prepare_for_upload(marketplace=marketplace)]},
                file,
            )
            file.flush()
            file.seek(0)

            filename = file.name

            if not is_win_os:
                return client.import_incident_fields(file=filename)

        # This section only runs if Windows is the detected operating system
        res = client.import_incident_fields(file=filename)
        # Delete the NamedTemporaryFile object
        Path(filename).unlink()
        return res

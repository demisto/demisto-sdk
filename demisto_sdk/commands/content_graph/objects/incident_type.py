from typing import Optional, Set

from pydantic import Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class IncidentType(ContentItem, content_type=ContentType.INCIDENT_TYPE):  # type: ignore[call-arg]
    playbook: Optional[str] = Field("")
    hours: int
    days: int
    weeks: int
    closure_script: Optional[str] = Field("", alias="closureScript")

    def metadata_fields(self) -> Set[str]:
        return {
            "object_id",
            "name",
            "playbook",
            "closure_script",
            "hours",
            "days",
            "weeks",
            "fromversion",
            "toversion",
        }

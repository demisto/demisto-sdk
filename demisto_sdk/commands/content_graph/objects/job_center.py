from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import JOB_CENTERS_DIR
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class JobCenter(ContentItem, content_type=ContentType.JOB_CENTER):  # type: ignore[call-arg]
    """An AgentiX Job Center job, authored under ``Packs/<Pack>/JobCenters/``.

    Not to be confused with the legacy XSOAR ``Job`` (``Jobs/job-*.json``).
    """

    version: int = -1
    system: Optional[bool] = None
    locked: Optional[bool] = None
    job_type: str = Field("", alias="jobType")
    job_name: str = Field("", alias="jobName")
    uniqueness_key: Optional[str] = Field(None, alias="uniquenessKey")
    job_metadata: Dict[str, Any] = Field({}, alias="metadata", exclude=True)
    entity_type: Optional[str] = Field(None, alias="entityType")
    entity_id: Optional[str] = Field(None, alias="entityId")
    assignee: Optional[str] = None
    status: Optional[str] = None
    trigger_type: str = Field("", alias="triggerType")
    trigger_spec: Optional[Dict[str, Any]] = Field(
        None, alias="triggerSpec", exclude=True
    )
    queue_policy: Optional[str] = Field(None, alias="queuePolicy")

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Match a ``.yml`` file located directly under a ``JobCenters`` folder."""
        return (
            isinstance(_dict, dict)
            and path.parent.name == JOB_CENTERS_DIR
            and path.suffix == ".yml"
            and "id" in _dict
            and "jobType" in _dict
        )

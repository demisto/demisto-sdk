from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.job_center import (
    StrictJobCenter,
)


def _optional_str(value: Any) -> Optional[str]:
    """Return ``None`` for a missing/null value, otherwise its string form."""
    return None if value is None else str(value)


def _required_str(value: Any) -> str:
    """Return ``""`` for a missing/null value, otherwise its string form."""
    return "" if value is None else str(value)


def _optional_bool(value: Any) -> Optional[bool]:
    """Return the value only if it is a real bool, otherwise ``None``."""
    return value if isinstance(value, bool) else None


class JobCenterParser(YAMLContentItemParser, content_type=ContentType.JOB_CENTER):
    """Parser for AgentiX Job Center jobs (``Packs/<Pack>/JobCenters/*.yml``)."""

    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )
        # Null or wrongly typed values are normalized so the graph model still
        # builds; the raw YAML is reported by the strict (ST110) validation instead.
        self.system: Optional[bool] = _optional_bool(self.yml_data.get("system"))
        self.locked: Optional[bool] = _optional_bool(self.yml_data.get("locked"))
        self.job_type: str = _required_str(self.yml_data.get("jobType"))
        self.job_name: str = _required_str(self.yml_data.get("jobName"))
        self.uniqueness_key: Optional[str] = _optional_str(
            self.yml_data.get("uniquenessKey")
        )
        metadata = self.yml_data.get("metadata")
        self.job_metadata: Dict[str, Any] = (
            metadata if isinstance(metadata, dict) else {}
        )
        self.entity_type: Optional[str] = _optional_str(self.yml_data.get("entityType"))
        self.entity_id: Optional[str] = _optional_str(self.yml_data.get("entityId"))
        self.assignee: Optional[str] = _optional_str(self.yml_data.get("assignee"))
        self.status: Optional[str] = _optional_str(self.yml_data.get("status"))
        self.trigger_type: str = _required_str(self.yml_data.get("triggerType"))
        trigger_spec = self.yml_data.get("triggerSpec")
        self.trigger_spec: Optional[Dict[str, Any]] = (
            trigger_spec if isinstance(trigger_spec, dict) else None
        )
        self.queue_policy: Optional[str] = _optional_str(
            self.yml_data.get("queuePolicy")
        )

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {
                "object_id": "commonfields.id",
                "version": "commonfields.version",
            }
        )
        return super().field_mapping

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.PLATFORM,
        }

    @property
    def fromversion(self) -> str:
        return str(
            get_value(
                self.yml_data,
                self.field_mapping.get("fromversion", ""),
                FILETYPE_TO_DEFAULT_FROMVERSION[FileType.JOB_CENTER],
            )
        )

    @property
    def strict_object(self):
        return StrictJobCenter

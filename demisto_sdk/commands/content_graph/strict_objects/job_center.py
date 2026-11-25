"""Strict (ST110) schema for the AgentiX Job Center ``JobCenter`` content item.

The rules mirror the server-side validation (``domain/jobCenter.go`` and
``services/jobcenter/validation.go``).
"""

from typing import Any, Dict, List, Optional

from pydantic import Extra, Field, constr, root_validator, validator

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    BaseOptionalVersionYaml,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    BaseStrictModel,
    SupportedFeaturesList,
    create_model,
)

# Server bounds are tenant-configurable; these are the server defaults.
JOB_NAME_MAX_LENGTH = 128
# Port of the server's RE2 jobNamePattern. Two Python/RE2 differences are bridged:
# RE2's ``\s`` is ASCII-only, so it is spelled out as ``[\t\n\f\r ]`` (Python's
# ``\s`` would also accept ``\v`` and Unicode spaces such as U+00A0), and ``\Z`` is
# used instead of ``$``, which in Python also matches before a trailing newline.
_JOB_NAME_EDGE_CHAR = r"[a-zA-Z0-9_\-\.\(\)\[\]]"
_JOB_NAME_INNER_CHAR = r"[a-zA-Z0-9_\-\.\t\n\f\r \(\)\[\]]"
JOB_NAME_REGEX = (
    rf"^(?:{_JOB_NAME_EDGE_CHAR}"
    rf"|{_JOB_NAME_EDGE_CHAR}{_JOB_NAME_INNER_CHAR}*{_JOB_NAME_EDGE_CHAR})\Z"
)
UNIQUENESS_KEY_MAX_LENGTH = 256
INTERVAL_MINUTES_MIN = 10
INTERVAL_MINUTES_MAX = 120
INTERVAL_COUNT_MAX = 12

AGENT_TO_ENTITY_REQUIRED_METADATA_KEYS = ("agent_id", "prompt_id")

# Like the other strict models, YAML numbers are coerced to strings by pydantic v1;
# the length and regex constraints are then applied to the coerced value.
JobNameStr = constr(min_length=1, max_length=JOB_NAME_MAX_LENGTH, regex=JOB_NAME_REGEX)
UniquenessKeyStr = constr(min_length=1, max_length=UNIQUENESS_KEY_MAX_LENGTH)
EntityIdStr = constr(min_length=1)


class JobCenterJobType(StrEnum):
    AGENT_TO_ENTITY = "agent_to_entity"


class JobCenterEntityType(StrEnum):
    CASE = "case"


class JobCenterStatus(StrEnum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    DONE = "DONE"
    DONE_MANUALLY = "DONE_MANUALLY"
    TERMINATED = "TERMINATED"


class JobCenterTriggerType(StrEnum):
    INTERVAL = "interval"
    ONETIME = "onetime"


class JobCenterQueuePolicy(StrEnum):
    SKIP = "skip"
    CANCEL_PREV = "cancel_prev"
    CONCURRENT = "concurrent"


def _is_strict_int(value: Any) -> bool:
    """Return True for real integers (bool is excluded)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_present(value: Any) -> bool:
    """Return True unless the value is None or an empty string."""
    return value is not None and value != ""


class _StrictJobCenter(BaseStrictModel):
    class Config:
        """
        Unknown top-level fields are ignored (not forbidden), consistent with
        Knowledge, so a job carrying a field not yet modeled here does not fail ST110.
        """

        extra = Extra.ignore

    supportedFeatures: Optional[SupportedFeaturesList] = None
    id_: str = Field(..., alias="id")
    version: int
    name: str
    description: Optional[str] = None
    system: Optional[bool] = None
    locked: Optional[bool] = None
    marketplaces: Optional[List[MarketplaceVersions]] = None
    supportedModules: Optional[List[str]] = Field(None, alias="supportedModules")

    job_type: JobCenterJobType = Field(..., alias="jobType")
    job_name: JobNameStr = Field(..., alias="jobName")  # type:ignore[valid-type]
    uniqueness_key: Optional[UniquenessKeyStr] = Field(  # type:ignore[valid-type]
        None, alias="uniquenessKey"
    )
    job_metadata: Dict[str, Any] = Field(..., alias="metadata")
    entity_type: Optional[JobCenterEntityType] = Field(None, alias="entityType")
    entity_id: Optional[EntityIdStr] = Field(  # type:ignore[valid-type]
        None, alias="entityId"
    )
    assignee: Optional[str] = None
    status: Optional[JobCenterStatus] = None
    trigger_type: JobCenterTriggerType = Field(..., alias="triggerType")
    trigger_spec: Optional[Dict[str, Any]] = Field(None, alias="triggerSpec")
    queue_policy: Optional[JobCenterQueuePolicy] = Field(None, alias="queuePolicy")

    @validator("id_")
    def validate_id_not_empty(cls, value):
        """Ensure the top-level ``id`` is a non-empty, non-whitespace string."""
        assert isinstance(value, str) and value.strip(), "id must be a non-empty string"
        return value

    @validator("job_metadata", "trigger_spec", pre=True)
    def validate_is_mapping(cls, value):
        """Reject non-mapping values (pydantic v1 would otherwise try ``dict(value)``)."""
        assert value is None or isinstance(value, dict), "must be a mapping"
        return value

    @root_validator(skip_on_failure=True)
    def validate_job_rules(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Cross-field rules enforced by the server on job creation."""
        if values.get("job_type") == JobCenterJobType.AGENT_TO_ENTITY:
            metadata = values.get("job_metadata") or {}
            missing = [
                key
                for key in AGENT_TO_ENTITY_REQUIRED_METADATA_KEYS
                # Server nonEmptyString: must be a string and != "" (no coercion).
                if not (isinstance(metadata.get(key), str) and metadata[key] != "")
            ]
            if missing:
                raise ValueError(
                    f"metadata must contain non-empty string(s) {missing} "
                    f"when jobType is '{JobCenterJobType.AGENT_TO_ENTITY}'"
                )

        # Like the server (``*job.EntityID == ""`` counts as missing), an empty
        # value is treated as absent.
        if _is_present(values.get("entity_type")) != _is_present(
            values.get("entity_id")
        ):
            raise ValueError(
                "entityType and entityId must be provided together (non-empty)"
            )

        trigger_spec = values.get("trigger_spec")
        if values.get("trigger_type") == JobCenterTriggerType.INTERVAL:
            if trigger_spec is None:
                raise ValueError(
                    f"triggerSpec is required when triggerType is '{JobCenterTriggerType.INTERVAL}'"
                )
            interval = trigger_spec.get("intervalMinutes")
            if not _is_strict_int(interval) or not (
                INTERVAL_MINUTES_MIN <= interval <= INTERVAL_MINUTES_MAX
            ):
                raise ValueError(
                    "triggerSpec.intervalMinutes must be an integer between "
                    f"{INTERVAL_MINUTES_MIN} and {INTERVAL_MINUTES_MAX}"
                )
            count = trigger_spec.get("count")
            if not _is_strict_int(count) or not (0 < count <= INTERVAL_COUNT_MAX):
                raise ValueError(
                    f"triggerSpec.count must be an integer greater than 0 and at most {INTERVAL_COUNT_MAX}"
                )
            # A recurring job must state what happens when a run is still active.
            if not _is_present(values.get("queue_policy")):
                raise ValueError(
                    f"queuePolicy is required when triggerType is '{JobCenterTriggerType.INTERVAL}'"
                )
        return values


StrictJobCenter = create_model(
    model_name="StrictJobCenter",
    base_models=(
        _StrictJobCenter,
        BaseOptionalVersionYaml,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)

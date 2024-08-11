from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.common import (
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    SUFFIXED_ID_DYNAMIC_MODEL,
    BaseStrictModel,
    create_model,
)


class HumanCron(BaseStrictModel):
    time_period_type: Optional[str] = Field(None, alias="timePeriodType")
    time_period: Optional[int] = Field(None, alias="timePeriod")


class _StrictJob(BaseStrictModel):
    id_: str = Field(alias="id")
    custom_fields: Optional[Any] = Field(None, alias="CustomFields")
    account: Optional[str] = None
    autime: Optional[int] = None
    type_: Optional[str] = Field(None, alias="type")
    raw_type: Optional[str] = Field(None, alias="rawType")
    name: str
    raw_name: Optional[str] = Field(None, alias="rawName")
    status: Optional[int] = None
    reason: Optional[str] = None
    created: Optional[str] = None
    occurred: Optional[str] = None
    closed: Optional[str] = None
    sla: Optional[int] = None
    severity: Optional[int] = None
    investigation_id: Optional[str] = Field(None, alias="investigationId")
    labels: Optional[Any] = None
    attachment: Optional[Any] = None
    details: str
    open_duration: Optional[int] = Field(None, alias="openDuration")
    last_open: Optional[str] = Field(None, alias="lastOpen")
    closing_user_id: Optional[str] = Field(None, alias="closingUserId")
    owner: Optional[str] = None
    activated: Optional[str] = None
    close_reason: Optional[str] = Field(None, alias="closeReason")
    raw_close_reason: Optional[str] = Field(None, alias="rawCloseReason")
    close_notes: Optional[str] = Field(None, alias="closeNotes")
    playbook_id: str = Field(alias="playbookId")
    due_date: Optional[str] = Field(None, alias="dueDate")
    reminder: Optional[str] = None
    run_status: Optional[str] = Field(None, alias="runStatus")
    notify_time: Optional[str] = Field(None, alias="notifyTime")
    phase: Optional[str] = None
    raw_phase: Optional[str] = Field(None, alias="rawPhase")
    is_playground: Optional[bool] = Field(None, alias="isPlayground")
    raw_json: Optional[str] = Field(None, alias="rawJSON")
    parent: Optional[str] = None
    category: Optional[str] = None
    raw_category: Optional[str] = Field(None, alias="rawCategory")
    linked_incidents: Optional[Any] = Field(None, alias="linkedIncidents")
    linked_count: Optional[int] = Field(None, alias="linkedCount")
    dropped_count: Optional[int] = Field(None, alias="droppedCount")
    source_instance: Optional[str] = Field(None, alias="sourceInstance")
    source_brand: Optional[str] = Field(None, alias="sourceBrand")
    canvases: Optional[Any] = None
    last_job_run_time: Optional[str] = Field(None, alias="lastJobRunTime")
    feed_based: Optional[bool] = Field(None, alias="feedBased")
    dbot_mirror_id: Optional[str] = Field(None, alias="dbotMirrorId")
    dbot_mirror_instance: Optional[str] = Field(None, alias="dbotMirrorInstance")
    dbot_mirror_direction: Optional[str] = Field(None, alias="dbotMirrorDirection")
    dbot_dirty_fields: Optional[Any] = Field(None, alias="dbotDirtyFields")
    dbot_current_dirty_fields: Optional[Any] = Field(
        None, alias="dbotCurrentDirtyFields"
    )
    dbot_mirror_tags: Optional[Any] = Field(None, alias="dbotMirrorTags")
    dbot_mirror_last_sync: Optional[str] = Field(None, alias="dbotMirrorLastSync")
    is_debug: Optional[bool] = Field(None, alias="isDebug")
    start_date: Optional[str] = Field(None, alias="startDate")
    times: Optional[int] = None
    recurrent: Optional[bool] = None
    ending_date: Optional[str] = Field(None, alias="endingDate")
    human_cron: Optional[HumanCron] = Field(None, alias="humanCron")
    timezone_offset: Optional[int] = Field(None, alias="timezoneOffset")
    cron_view: Optional[bool] = Field(None, alias="cronView")
    timezone: Optional[str] = None
    scheduled: Optional[bool] = None
    pack_id: Optional[str] = Field(None, alias="packID")
    item_version: Optional[str] = Field(None, alias="itemVersion")
    from_version: str = Field(alias="fromVersion")
    to_server_version: Optional[str] = Field(None, alias="toServerVersion")
    propagation_labels: Optional[Any] = Field(None, alias="propagationLabels")
    definition_id: Optional[str] = Field(None, alias="definitionId")
    minutes_to_timeout: Optional[int] = Field(None, alias="minutesToTimeout")
    description: Optional[str] = None
    current_incident_id: Optional[str] = Field(None, alias="currentIncidentId")
    last_run_time: Optional[str] = Field(None, alias="lastRunTime")
    next_run_time: Optional[str] = Field(None, alias="nextRunTime")
    display_next_run_time: Optional[str] = Field(None, alias="displayNextRunTime")
    disabled_next_run_time: Optional[str] = Field(None, alias="disabledNextRunTime")
    scheduling_status: Optional[str] = Field(None, alias="schedulingStatus")
    previous_run_status: Optional[str] = Field(None, alias="previousRunStatus")
    tags: Optional[List[str]] = None
    should_trigger_new: Optional[bool] = Field(None, alias="shouldTriggerNew")
    close_prev_run: Optional[bool] = Field(None, alias="closePrevRun")
    notify_owner: Optional[bool] = Field(None, alias="notifyOwner")
    is_feed: bool = Field(alias="isFeed")
    selected_feeds: List[str] = Field(alias="selectedFeeds")
    is_all_feeds: bool = Field(alias="isAllFeeds")
    locked: Optional[bool] = None
    system: Optional[bool] = None


StrictJob = create_model(
    model_name="StrictJob",
    base_models=(
        _StrictJob,
        NAME_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        SUFFIXED_ID_DYNAMIC_MODEL,
    ),
)

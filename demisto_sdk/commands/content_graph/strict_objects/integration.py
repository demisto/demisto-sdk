from typing import Any, List, Optional

from pydantic import Field, conlist, validator

from demisto_sdk.commands.common.constants import (
    TYPE_PYTHON2,
    TYPE_PYTHON3,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    Argument,
    BaseIntegrationScript,
    BaseStrictModel,
    CommonFields,
    Important,
    Output,
    ScriptType,
)
from demisto_sdk.commands.content_graph.strict_objects.common import (
    DEFAULT_DYNAMIC_MODEL_LOWER_CASE,
    DEPRECATED_DYNAMIC_MODEL,
    DESCRIPTION_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    REQUIRED_DYNAMIC_MODEL,
    create_dynamic_model,
    create_model,
)

IS_FETCH_DYNAMIC_MODEL = create_dynamic_model(
    field_name="isfetch",
    type_=Optional[bool],
    default=None,
)
IS_FETCH_EVENTS_DYNAMIC_MODEL = create_dynamic_model(
    field_name="isfetchevents",
    type_=Optional[bool],
    default=None,
)


class _Configuration(BaseStrictModel):
    display: Optional[str] = None
    section: Optional[str] = None
    advanced: Optional[str] = None
    default_value: Optional[Any] = Field(None, alias="defaultvalue")
    name: str
    type: int
    required: Optional[bool] = None
    hidden: Optional[Any] = None
    options: Optional[List[str]] = None
    additional_info: Optional[str] = Field(None, alias="additionalinfo")
    display_password: Optional[str] = Field(None, alias="displaypassword")
    hidden_username: Optional[bool] = Field(None, alias="hiddenusername")
    hidden_password: Optional[bool] = Field(None, alias="hiddenpassword")
    from_license: Optional[str] = Field(None, alias="fromlicense")


Configuration = create_model(
    model_name="Configuration",
    base_models=(
        _Configuration,
        REQUIRED_DYNAMIC_MODEL,
        DEFAULT_DYNAMIC_MODEL_LOWER_CASE,
        NAME_DYNAMIC_MODEL,
    ),
)


class IntegrationOutput(Output):  # type:ignore[misc,valid-type]
    important: Optional[bool] = None  # not the Important class
    important_description: Optional[str] = Field(None, alias="importantDescription")


class _Command(BaseStrictModel):
    name: str
    execution: Optional[bool] = None
    description: str
    deprecated: Optional[bool] = None
    system: Optional[bool] = None
    arguments: Optional[List[Argument]] = None  # type:ignore[valid-type]
    outputs: Optional[List[IntegrationOutput]] = None
    important: Optional[List[Important]] = None  # type:ignore[valid-type]
    timeout: Optional[int] = None
    hidden: Optional[bool] = None
    polling: Optional[bool] = None
    prettyname: Optional[str] = None
    quickaction: Optional[bool] = None


Command = create_model(
    model_name="Command",
    base_models=(
        _Command,
        DEPRECATED_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
    ),
)


class _Script(BaseStrictModel):
    script: str
    type_: ScriptType = Field(..., alias="type")
    docker_image: str = Field(None, alias="dockerimage")
    alt_docker_images: Optional[List[str]] = Field(None, alias="alt_dockerimages")
    native_image: Optional[List[str]] = Field(None, alias="nativeImage")
    is_fetch: Optional[bool] = Field(None, alias="isfetch")
    is_fetch_events: Optional[bool] = Field(None, alias="isfetchevents")
    is_fetch_assets: Optional[bool] = Field(None, alias="isfetchassets")
    long_running: Optional[bool] = Field(None, alias="longRunning")
    long_running_port: Optional[bool] = Field(None, alias="longRunningPort")
    is_mappable: Optional[bool] = Field(None, alias="ismappable")
    is_remote_sync_in: Optional[bool] = Field(None, alias="isremotesyncin")
    is_remote_sync_out: Optional[bool] = Field(None, alias="isremotesyncout")
    commands: Optional[List[Command]] = None  # type:ignore[valid-type]
    run_once: Optional[bool] = Field(None, alias="runonce")
    sub_type: Optional[str] = Field([TYPE_PYTHON2, TYPE_PYTHON3], alias="subtype")
    feed: Optional[bool] = None
    is_fetch_samples: Optional[bool] = Field(None, alias="isFetchSamples")
    reset_context: Optional[bool] = Field(None, alias="resetContext")


Script = create_model(
    model_name="Script",
    base_models=(_Script, IS_FETCH_DYNAMIC_MODEL, IS_FETCH_EVENTS_DYNAMIC_MODEL),
)


class _CommonFieldsIntegration(BaseStrictModel):
    sort_values: Optional[List[str]] = Field(None, alias="sortvalues")


CommonFieldsIntegration = create_model(
    model_name="CommonFieldsIntegration",
    base_models=(
        _CommonFieldsIntegration,
        CommonFields,
    ),
)


class SectionOrderValues(StrEnum):
    CONNECT = "Connect"
    COLLECT = "Collect"
    OPTIMIZE = "Optimize"
    MIRRORING = "Mirroring"


class _StrictIntegration(BaseStrictModel):
    common_fields: CommonFieldsIntegration = Field(..., alias="commonfields")  # type:ignore[valid-type]
    display: str
    beta: Optional[bool] = None
    category: str
    section_order: Optional[conlist(SectionOrderValues, min_items=1, max_items=4)] = (  # type:ignore[valid-type]
        Field(alias="sectionorder")
    )
    configurations: List[Configuration] = Field(..., alias="configuration")  # type:ignore[valid-type]
    image: Optional[str] = None
    description: str
    default_mapper_in: Optional[str] = Field(None, alias="defaultmapperin")
    default_mapper_out: Optional[str] = Field(None, alias="defaultmapperout")
    default_classifier: Optional[str] = Field(None, alias="defaultclassifier")
    detailed_description: Optional[str] = Field(None, alias="detaileddescription")
    auto_config_instance: Optional[bool] = Field(None, alias="autoconfiginstance")
    support_level_header: MarketplaceVersions = Field(None, alias="supportlevelheader")
    script: Script  # type:ignore[valid-type]
    hidden: Optional[bool] = None
    videos: Optional[List[str]] = None
    versioned_fields: dict = Field(None, alias="versionedfields")
    default_enabled: Optional[bool] = Field(None, alias="defaultEnabled")
    script_not_visible: Optional[bool] = Field(None, alias="scriptNotVisible")
    hybrid: Optional[bool] = None
    supports_quick_actions: Optional[bool] = Field(None, alias="supportsquickactions")

    def __init__(self, **data):
        """
        Initializes the _StrictIntegration object.
        Using this custom init function to support two aliases for the section_order field.
        """
        if "sectionOrder" in data and "sectionorder" not in data:
            data["sectionorder"] = data.pop("sectionOrder")
        elif "sectionOrder" in data and "sectionorder" in data:
            data["sectionorder"] = list(
                set(data["section_order"]) | set(data["section_order_camel_case"])
            )
        super().__init__(**data)

    @validator("configurations")
    def validate_sections(cls, configurations, values):
        """
        Validates each configuration object has a valid section clause.
        A valid section clause is a section which is included in the list of the integration's section_order.
        Even if the section is an allowed value (currently Collect, Connect or Optimize),it could be invalid if the
        specific value is not present in section_order.
        """
        section_order_field = values.get("section_order")
        if not section_order_field:
            return configurations
        integration_sections = [
            section_name.value for section_name in section_order_field
        ]
        for config in configurations:
            if not config.section:
                return configurations
            assert (
                config.section in integration_sections
            ), f"section {config.section} of {config.display} is not present in section_order {integration_sections}"
        return configurations


StrictIntegration = create_model(
    model_name="StrictIntegration",
    base_models=(
        _StrictIntegration,
        BaseIntegrationScript,
        IS_FETCH_DYNAMIC_MODEL,
        IS_FETCH_EVENTS_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)

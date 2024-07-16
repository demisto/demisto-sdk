from typing import Any, List, Optional

from pydantic import Field

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    DESCRIPTION_DYNAMIC_MODEL,
    Argument,
    BaseIntegrationScript,
    BaseStrictModel,
    CommonFields,
    Important,
    Output,
    ScriptType,
    create_dynamic_model,
)
from demisto_sdk.commands.content_graph.strict_objects.common import create_model

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


class Configuration(BaseStrictModel):
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
    default_value_xsoar: Optional[Any] = Field(None, alias="defaultvalue:xsoar")
    default_value_marketplace_v2: Optional[Any] = Field(
        None, alias="defaultvalue:marketplacev2"
    )
    default_value_xpanse: Optional[Any] = Field(None, alias="defaultvalue:xpanse")
    default_value_xsoar_saas: Optional[Any] = Field(
        None, alias="defaultvalue:xsoar_saas"
    )
    default_value_xsoar_on_prem: Optional[Any] = Field(
        None, alias="defaultvalue:xsoar_on_prem"
    )
    name_xsoar: Optional[str] = Field(None, alias="name:xsoar")
    name_marketplacev2: Optional[str] = Field(None, alias="name:marketplacev2")
    name_xpanse: Optional[str] = Field(None, alias="name:xpanse")
    name_xsoar_saas: Optional[str] = Field(None, alias="name:xsoar_saas")
    name_xsoar_on_prem: Optional[str] = Field(None, alias="name:xsoar_on_prem")
    required_xsoar: Optional[bool] = Field(None, alias="required:xsoar")
    required_marketplacev2: Optional[bool] = Field(None, alias="required:marketplacev2")
    required_xpanse: Optional[bool] = Field(None, alias="required:xpanse")
    required_xsoar_saas: Optional[bool] = Field(None, alias="required:xsoar_saas")
    required_xsoar_on_prem: Optional[bool] = Field(None, alias="required:xsoar_on_prem")


class IntegrationOutput(Output):
    important: Optional[bool] = None  # not the Important class
    important_description: Optional[str] = Field(None, alias="importantDescription")


class Command(BaseStrictModel):
    name: str
    execution: Optional[bool] = None
    description: str
    deprecated: Optional[bool] = None
    system: Optional[bool] = None
    arguments: Optional[List[Argument]] = None
    outputs: Optional[List[IntegrationOutput]] = None
    important: Optional[List[Important]] = None
    timeout: Optional[int] = None
    hidden: Optional[bool] = None
    polling: Optional[bool] = None
    name_xsoar: Optional[str] = Field(None, alias="name:xsoar")
    name_marketplacev2: Optional[str] = Field(None, alias="name:marketplacev2")
    name_xpanse: Optional[str] = Field(None, alias="name:xpanse")
    name_xsoar_saas: Optional[str] = Field(None, alias="name:xsoar_saas")
    name_xsoar_on_prem: Optional[str] = Field(None, alias="name:xsoar_on_prem")
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(
        None, alias="description:marketplacev2"
    )
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(
        None, alias="description:xsoar_on_prem"
    )
    deprecated_xsoar: Optional[bool] = Field(None, alias="deprecated:xsoar")
    deprecated_marketplace_v2: Optional[bool] = Field(
        None, alias="deprecated:marketplacev2"
    )
    deprecated_xpanse: Optional[bool] = Field(None, alias="deprecated:xpanse")
    deprecated_xsoar_saas: Optional[bool] = Field(None, alias="deprecated:xsoar_saas")
    deprecated_xsoar_on_prem: Optional[bool] = Field(
        None, alias="deprecated:xsoar_on_prem"
    )


class _Script(BaseStrictModel):
    script: str
    type_: ScriptType = Field(..., alias="type")
    docker_image: str = Field(None, alias="dockerimage")
    docker_image_45: str = Field(None, alias="dockerimage45")
    alt_docker_images: Optional[List[str]] = Field(None, alias="alt_dockerimages")
    native_image: Optional[List[str]] = Field(None, alias="nativeImage")
    is_fetch: Optional[bool] = Field(None, alias="isfetch")
    is_fetch_events: Optional[bool] = Field(None, alias="isfetchevents")
    is_fetch_assets: Optional[bool] = Field(None, alias="isfetchassets")
    long_running: Optional[bool] = Field(None, alias="longRunning")
    long_running_port: Optional[bool] = Field(None, alias="longRunningPort")
    is_mappable: Optional[bool] = Field(None, alias="ismappable")
    is_remote_sync_in: Optional[bool] = Field(None, alias="isremotesyncin")
    is_remote_sync_in_x2: Optional[bool] = Field(None, alias="isremotesyncin_x2")
    is_remote_sync_out: Optional[bool] = Field(None, alias="isremotesyncout")
    is_remote_sync_out_x2: Optional[bool] = Field(None, alias="isremotesyncout_x2")
    commands: Optional[List[Command]] = None
    run_once: Optional[bool] = Field(None, alias="runonce")
    sub_type: Optional[str] = Field(["python2", "python3"], alias="subtype")
    feed: Optional[bool] = None
    is_fetch_samples: Optional[bool] = Field(None, alias="isFetchSamples")
    reset_context: Optional[bool] = Field(None, alias="resetContext")


Script = create_model(
    model_name="Script",
    base_models=(_Script, IS_FETCH_DYNAMIC_MODEL, IS_FETCH_EVENTS_DYNAMIC_MODEL),
)


class CommonFieldsIntegration(CommonFields):
    sort_values: Optional[List[str]] = Field(None, alias="sortvalues")


class _StrictIntegration(BaseIntegrationScript):
    common_fields: CommonFieldsIntegration = Field(..., alias="commonfields")
    display: str
    beta: Optional[bool] = None
    category: str
    section_order_1: Optional[List[str]] = Field(None, alias="sectionOrder")
    section_order_2: Optional[List[str]] = Field(None, alias="sectionorder")
    image: Optional[str] = None
    description: str
    default_mapper_in: Optional[str] = Field(None, alias="defaultmapperin")
    default_mapper_out: Optional[str] = Field(None, alias="defaultmapperout")
    default_mapper_out_x2: Optional[str] = Field(None, alias="defaultmapperout_x2")
    default_classifier: Optional[str] = Field(None, alias="defaultclassifier")
    detailed_description: Optional[str] = Field(None, alias="detaileddescription")
    auto_config_instance: Optional[bool] = Field(None, alias="autoconfiginstance")
    support_level_header: MarketplaceVersions = Field(None, alias="supportlevelheader")
    configuration: List[Configuration]
    script: Script  # type:ignore[valid-type]
    hidden: Optional[bool] = None
    videos: Optional[List[str]] = None
    versioned_fields: dict = Field(None, alias="versionedfields")
    default_enabled: Optional[bool] = Field(None, alias="defaultEnabled")
    script_not_visible: Optional[bool] = Field(None, alias="scriptNotVisible")
    hybrid: Optional[bool] = None


StrictIntegration = create_model(
    model_name="StrictIntegration",
    base_models=(
        _StrictIntegration,
        IS_FETCH_DYNAMIC_MODEL,
        IS_FETCH_EVENTS_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
    ),
)

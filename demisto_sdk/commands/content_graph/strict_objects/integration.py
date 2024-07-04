from typing import Optional, Any

from base_strict_model import BaseStrictModel
from pydantic import Field


class Script(BaseStrictModel):
    script: str
    type_: str = Field(['javascript', 'python', 'powershell'], alias="type")
    docker_image: str = Field(None, alias="dockerimage")
    docker_image_45: str = Field(None, alias="dockerimage45")
    alt_docker_images: Optional[list[str]] = Field(None, alias="alt_dockerimages")
    native_image: Optional[list[str]] = Field(None, alias="nativeImage")
    is_fetch: Optional[bool] = Field(False, alias="isfetch")
    is_fetch_events: Optional[bool] = Field(False, alias="isfetchevents")
    is_fetch_assets: Optional[bool] = Field(False, alias="isfetchassets")
    long_running: Optional[bool] = Field(False, alias="longRunning")
    long_running_port: Optional[bool] = Field(False, alias="longRunningPort")
    is_mappable: Optional[bool] = Field(False, alias="ismappable")
    is_remote_sync_in: Optional[bool] = Field(False, alias="isremotesyncin")
    is_remote_sync_in_x2: Optional[bool] = Field(False, alias="isremotesyncin_x2")
    is_remote_sync_out: Optional[bool] = Field(False, alias="isremotesyncout")
    is_remote_sync_out_x2: Optional[bool] = Field(False, alias="isremotesyncout_x2")
    #TODO
    commands: Optional[list[command_schema]] = Field(None)
    run_once: Optional[bool] = Field(False, alias="runonce")
    sub_type: Optional[str] = Field(['python2', 'python3'], alias="subtype")
    feed: Optional[bool] = Field(False)
    is_fetch_samples: Optional[bool] = Field(False, alias="isFetchSamples")
    reset_context: Optional[bool] = Field(False, alias="resetContext")
    is_fetch_xsoar: Optional[bool] = Field(False, alias="isfetch:xsoar")
    is_fetch_marketplace_v2: Optional[bool] = Field(False, alias="isfetch:marketplacev2")
    is_fetch_xpanse: Optional[bool] = Field(False, alias="isfetch:xpanse")
    is_fetch_xsoar_saas: Optional[bool] = Field(False, alias="isfetch:xsoar_saas")
    is_fetch_xsoar_on_prem: Optional[bool] = Field(False, alias="isfetch:xsoar_on_prem")
    is_fetch_events_xsoar: Optional[bool] = Field(False, alias="isfetchevents:xsoar")
    is_fetch_events_marketplace_v2: Optional[bool] = Field(False, alias="isfetchevents:marketplacev2")
    is_fetch_events_xpanse: Optional[bool] = Field(False, alias="isfetchevents:xpanse")
    is_fetch_events_xsoar_saas: Optional[bool] = Field(False, alias="isfetchevents:xsoar_saas")
    is_fetch_events_xsoar_on_prem: Optional[bool] = Field(False, alias="isfetchevents:xsoar_on_prem")


class CommonFields(BaseStrictModel):
    id_: str = Field(..., alias="id")
    version: int

    #TODO sortvalues??

    id_xsoar: str = Field(None, alias="id:xsoar")
    id_marketplacev2: str = Field(None, alias="id:marketplacev2")
    id_xsoar_saas: str = Field(None, alias="id:xsoar_saas")
    id_xsoar_on_prem: str = Field(None, alias="id:xsoar_on_prem")


class StrictIntegration(BaseStrictModel):
    common_fields: CommonFields = Field(..., alias="commonfields")
    name: str
    display: str
    deprecated: bool = Field(False)
    beta: bool = Field(False)
    category: str
    section_order_1: Optional[list[str]] = Field([], alias="sectionOrder")
    section_order_2: Optional[list[str]] = Field([], alias="sectionorder")
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    image: Optional[str] = Field(None)
    description: str
    default_mapper_in: Optional[str] = Field(None, alias="defaultmapperin")
    default_mapper_out: Optional[str] = Field(None, alias="defaultmapperout")
    default_mapper_out_x2: Optional[str] = Field(None, alias="defaultmapperout_x2")
    default_classifier: Optional[str] = Field(None, alias="defaultclassifier")
    detailed_description: Optional[str] = Field(None, alias="detaileddescription")
    auto_config_instance: Optional[bool] = Field(False, alias="autoconfiginstance")
    # TODO - ENUM
    support_level_header: Optional[str] = Field(['xsoar', 'partner', 'community'], alias="supportlevelheader")
    configuration: configuration_schema # TODO
    script: Script
    system: Optional[bool] = Field(False)
    hidden: Optional[bool] = Field(False)
    videos: Optional[list[str]] = Field(None)
    versioned_fields: Any = Field(None, alias="versionedfields")
    default_enabled: Optional[bool] = Field(False, alias="defaultEnabled")
    tests: Optional[list[str]] = Field(None)
    script_not_visible: Optional[bool] = Field(False, alias="scriptNotVisible")
    auto_update_docker_image: Optional[bool] = Field(False, alias="autoUpdateDockerImage")
    #TODO
    marketplaces: Optional[str] = Field(['xsoar', 'marketplacev2', 'xpanse', 'xsoar_saas', 'xsoar_on_prem'])
    hybrid: Optional[bool] = Field(False)
    name_xsoar: Optional[str] = Field(None, alias="name:xsoar")
    name_marketplace_v2: Optional[str] = Field(None, alias="name:marketplacev2")
    name_xpanse: Optional[str] = Field(None, alias="name:xpanse")
    name_xsoar_saas: Optional[str] = Field(None, alias="name:xsoar_saas")
    name_xsoar_on_prem: Optional[str] = Field(None, alias="name:xsoar_on_prem")
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(None, alias="description:marketplacev2")
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(None, alias="description:xsoar_on_prem")
    deprecated_xsoar: Optional[bool] = Field(False, alias="deprecated:xsoar")
    deprecated_marketplace_v2: Optional[bool] = Field(False, alias="deprecated:marketplacev2")
    deprecated_xpanse: Optional[bool] = Field(False, alias="deprecated:xpanse")
    deprecated_xsoar_saas: Optional[bool] = Field(False, alias="deprecated:xsoar_saas")
    deprecated_xsoar_on_prem: Optional[bool] = Field(False, alias="deprecated:xsoar_on_prem")
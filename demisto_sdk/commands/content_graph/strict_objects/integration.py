from typing import Optional, Any, Union
from pydantic import Field
from demisto_sdk.commands.common.constants import MarketplaceVersions, Auto
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import BaseStrictModel


class Configuration(BaseStrictModel):
    display: Optional[str] = None
    section: Optional[str] = None
    advanced: Optional[str] = None
    default_value: Optional[Any] = Field(None, alias="defaultvalue")
    name: str
    type: int
    required: Optional[bool] = None
    hidden: Optional[Any] = None
    hidden_x2: bool = None
    options: Optional[list[str]] = None
    additional_info: Optional[str] = Field(None, alias="additionalinfo")
    display_password: Optional[str] = Field(None, alias="displaypassword")
    hidden_username: Optional[bool] = Field(None, alias="hiddenusername")
    hidden_password: Optional[bool] = Field(None, alias="hiddenpassword")
    from_license: Optional[str] = Field(None, alias="fromlicense")
    default_value_xsoar: Optional[Any] = Field(None, alias="defaultvalue:xsoar")
    default_value_marketplace_v2: Optional[Any] = Field(None, alias="defaultvalue:marketplacev2")
    default_value_xpanse: Optional[Any] = Field(None, alias="defaultvalue:xpanse")
    default_value_xsoar_saas: Optional[Any] = Field(None, alias="defaultvalue:xsoar_saas")
    default_value_xsoar_on_prem: Optional[Any] = Field(None, alias="defaultvalue:xsoar_on_prem")
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


class Important(BaseStrictModel):
    context_path: str = Field(..., alias="contextPath")
    description: str
    related: Optional[str] = None
    description_xsoar: Optional[str] = Field(None, alias="contextPath")
    description_marketplacev2: Optional[str] = Field(None, alias="description:marketplacev2")
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(None, alias="description:xsoar_on_prem")


class Output(BaseStrictModel):
    content_path: Optional[str] = Field(None, alias="contentPath")
    context_path: Optional[str] = Field(None, alias="contextPath")
    description: str
    important: Optional[bool] = None  # not the Important class
    important_description: Optional[str] = Field(None, alias="importantDescription")
    type: Optional[str] = None


class Argument(BaseStrictModel):
    name: str
    required: Optional[bool] = None
    default: Optional[bool] = None
    description: str
    auto: Optional[Auto] = None
    predefined: Optional[list[str]] = None
    is_array: Optional[bool] = Field(None, alias="isArray")
    default_value: Optional[Any] = Field(None, alias="defaultValue")
    secret: Optional[bool] = None
    deprecated: Optional[bool] = None
    type: Optional[str] = None
    hidden: Optional[bool] = None
    name_xsoar: Optional[str] = Field(None, alias="name:xsoar")
    name_marketplacev2: Optional[str] = Field(None, alias="name:marketplacev2")
    name_xpanse: Optional[str] = Field(None, alias="name:xpanse")
    name_xsoar_saas: Optional[str] = Field(None, alias="name:xsoar_saas")
    name_xsoar_on_prem: Optional[str] = Field(None, alias="name:xsoar_on_prem")
    required_xsoar: Optional[bool] = Field(None, alias="required:xsoar")
    required_marketplacev2: Optional[bool] = Field(None, alias="required:marketplacev2")
    required_xsoar_saas: Optional[bool] = Field(None, alias="required:xsoar_saas")
    required_xsoar_on_prem: Optional[bool] = Field(None, alias="required:xsoar_on_prem")
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(None, alias="description:marketplacev2")
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(None, alias="description:xsoar_on_prem")
    default_value_xsoar: Optional[Any] = Field(None, alias="defaultValue:xsoar")
    default_value_marketplace_v2: Optional[Any] = Field(None, alias="defaultValue:marketplacev2")
    default_value_xpanse: Optional[Any] = Field(None, alias="defaultValue:xpanse")
    default_value_xsoar_saas: Optional[Any] = Field(None, alias="defaultValue:xsoar_saas")
    default_value_xsoar_on_prem: Optional[Any] = Field(None, alias="defaultValue:xsoar_on_prem")
    deprecated_xsoar: Optional[bool] = Field(None, alias="deprecated:xsoar")
    deprecated_marketplace_v2: Optional[bool] = Field(None, alias="deprecated:marketplacev2")
    deprecated_xpanse: Optional[bool] = Field(None, alias="deprecated:xpanse")
    deprecated_xsoar_saas: Optional[bool] = Field(None, alias="deprecated:xsoar_saas")
    deprecated_xsoar_on_prem: Optional[bool] = Field(None, alias="deprecated:xsoar_on_prem")


class Command(BaseStrictModel):
    name: str
    execution: Optional[bool] = None
    description: str
    deprecated: Optional[bool] = None
    system: Optional[bool] = None
    arguments: Optional[list[Argument]] = None
    outputs: Optional[list[Output]] = None
    important: Optional[list[Important]] = None
    timeout: Optional[int] = None
    hidden: Optional[bool] = None
    hidden_x2: Optional[bool] = None
    polling: Optional[bool] = None
    name_xsoar: Optional[str] = Field(None, alias="name:xsoar")
    name_marketplacev2: Optional[str] = Field(None, alias="name:marketplacev2")
    name_xpanse: Optional[str] = Field(None, alias="name:xpanse")
    name_xsoar_saas: Optional[str] = Field(None, alias="name:xsoar_saas")
    name_xsoar_on_prem: Optional[str] = Field(None, alias="name:xsoar_on_prem")
    description_xsoar: Optional[str] = Field(None, alias="description:xsoar")
    description_marketplace_v2: Optional[str] = Field(None, alias="description:marketplacev2")
    description_xpanse: Optional[str] = Field(None, alias="description:xpanse")
    description_xsoar_saas: Optional[str] = Field(None, alias="description:xsoar_saas")
    description_xsoar_on_prem: Optional[str] = Field(None, alias="description:xsoar_on_prem")
    deprecated_xsoar: Optional[bool] = Field(None, alias="deprecated:xsoar")
    deprecated_marketplace_v2: Optional[bool] = Field(None, alias="deprecated:marketplacev2")
    deprecated_xpanse: Optional[bool] = Field(None, alias="deprecated:xpanse")
    deprecated_xsoar_saas: Optional[bool] = Field(None, alias="deprecated:xsoar_saas")
    deprecated_xsoar_on_prem: Optional[bool] = Field(None, alias="deprecated:xsoar_on_prem")


class Script(BaseStrictModel):
    script: str
    type_: str = Field(['javascript', 'python', 'powershell'], alias="type")
    docker_image: str = Field(None, alias="dockerimage")
    docker_image_45: str = Field(None, alias="dockerimage45")
    alt_docker_images: Optional[list[str]] = Field(None, alias="alt_dockerimages")
    native_image: Optional[list[str]] = Field(None, alias="nativeImage")
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
    commands: Optional[list[Command]] = None
    run_once: Optional[bool] = Field(None, alias="runonce")
    sub_type: Optional[str] = Field(['python2', 'python3'], alias="subtype")
    feed: Optional[bool] = None
    is_fetch_samples: Optional[bool] = Field(None, alias="isFetchSamples")
    reset_context: Optional[bool] = Field(None, alias="resetContext")
    is_fetch_xsoar: Optional[bool] = Field(None, alias="isfetch:xsoar")
    is_fetch_marketplace_v2: Optional[bool] = Field(None, alias="isfetch:marketplacev2")
    is_fetch_xpanse: Optional[bool] = Field(None, alias="isfetch:xpanse")
    is_fetch_xsoar_saas: Optional[bool] = Field(None, alias="isfetch:xsoar_saas")
    is_fetch_xsoar_on_prem: Optional[bool] = Field(None, alias="isfetch:xsoar_on_prem")
    is_fetch_events_xsoar: Optional[bool] = Field(None, alias="isfetchevents:xsoar")
    is_fetch_events_marketplace_v2: Optional[bool] = Field(None, alias="isfetchevents:marketplacev2")
    is_fetch_events_xpanse: Optional[bool] = Field(None, alias="isfetchevents:xpanse")
    is_fetch_events_xsoar_saas: Optional[bool] = Field(None, alias="isfetchevents:xsoar_saas")
    is_fetch_events_xsoar_on_prem: Optional[bool] = Field(None, alias="isfetchevents:xsoar_on_prem")


class CommonFields(BaseStrictModel):
    id_: str = Field(..., alias="id")
    version: int
    sort_values: Optional[list[str]] = Field(None, alias="sortvalues")
    id_xsoar: str = Field(None, alias="id:xsoar")
    id_marketplacev2: str = Field(None, alias="id:marketplacev2")
    id_xsoar_saas: str = Field(None, alias="id:xsoar_saas")
    id_xsoar_on_prem: str = Field(None, alias="id:xsoar_on_prem")


class StrictIntegration(BaseStrictModel):
    common_fields: CommonFields = Field(..., alias="commonfields")
    name: str
    display: str
    deprecated: bool = False
    beta: bool = False
    category: str
    section_order_1: Optional[list[str]] = Field(None, alias="sectionOrder")
    section_order_2: Optional[list[str]] = Field(None, alias="sectionorder")
    from_version: Optional[str] = Field(None, alias="fromversion")
    to_version: Optional[str] = Field(None, alias="toversion")
    image: Optional[str] = None
    description: str
    default_mapper_in: Optional[str] = Field(None, alias="defaultmapperin")
    default_mapper_out: Optional[str] = Field(None, alias="defaultmapperout")
    default_mapper_out_x2: Optional[str] = Field(None, alias="defaultmapperout_x2")
    default_classifier: Optional[str] = Field(None, alias="defaultclassifier")
    detailed_description: Optional[str] = Field(None, alias="detaileddescription")
    auto_config_instance: Optional[bool] = Field(None, alias="autoconfiginstance")
    support_level_header: MarketplaceVersions = Field(None, alias="supportlevelheader")
    configuration: list[Configuration]
    script: Script
    system: Optional[bool] = None
    hidden: Optional[bool] = None
    videos: Optional[list[str]] = None
    versioned_fields: dict = Field(None, alias="versionedfields")
    default_enabled: Optional[bool] = Field(None, alias="defaultEnabled")
    tests: Optional[list[str]] = None
    script_not_visible: Optional[bool] = Field(None, alias="scriptNotVisible")
    auto_update_docker_image: Optional[bool] = Field(None, alias="autoUpdateDockerImage")
    marketplaces: Union[MarketplaceVersions, list[MarketplaceVersions]] = None
    hybrid: Optional[bool] = None
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
    deprecated_xsoar: Optional[bool] = Field(None, alias="deprecated:xsoar")
    deprecated_marketplace_v2: Optional[bool] = Field(None, alias="deprecated:marketplacev2")
    deprecated_xpanse: Optional[bool] = Field(None, alias="deprecated:xpanse")
    deprecated_xsoar_saas: Optional[bool] = Field(None, alias="deprecated:xsoar_saas")
    deprecated_xsoar_on_prem: Optional[bool] = Field(None, alias="deprecated:xsoar_on_prem")


# content_packs = Path("/Users/rshunim/dev/demisto/content/Packs/")
# for file in content_packs.rglob("*/Integrations/*/*.yml"):
#     if "DeprecatedContent" in file.parts:
#         continue
#     print(file)
#     integration = StrictIntegration.parse_obj(get_file(file))
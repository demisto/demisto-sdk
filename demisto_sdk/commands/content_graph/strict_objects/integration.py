from typing import Annotated, Any, List, Optional

from pydantic import Field, conlist, validator

from demisto_sdk.commands.common.constants import (
    TYPE_PYTHON2,
    TYPE_PYTHON3,
    MarketplaceVersions,
    PlatformSupportedModules,
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
    HIDDEN_DYNAMIC_MODEL,
    NAME_DYNAMIC_MODEL,
    QUICK_ACTION_DYNAMIC_MODEL,
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


class SectionOrderValues(StrEnum):
    CONNECT = "Connect"
    COLLECT = "Collect"
    OPTIMIZE = "Optimize"
    MIRRORING = "Mirroring"
    RESULT = "Result"


class _Configuration(BaseStrictModel):
    display: Optional[str] = Field(
        None,
        description="Display label for this configuration parameter shown in the integration settings UI.",
    )
    section: Optional[str] = Field(
        None,
        description="Section name this parameter belongs to (e.g. 'Connect', 'Collect'). Must be listed in sectionorder.",
    )
    advanced: Optional[str] = Field(
        None,
        description="When set, marks this parameter as advanced and hides it by default in the UI.",
    )
    default_value: Optional[Any] = Field(
        None,
        alias="defaultvalue",
        description="Default value for this configuration parameter. Used when the user does not provide a value.",
    )
    name: str = Field(
        ...,
        description="Unique machine-readable name of this configuration parameter. Used in code to access the parameter value.",
    )
    type: int = Field(
        ...,
        description="Parameter type code. Common values: 0=Short text, 4=Encrypted, 8=Boolean, 9=Authentication, 12=Single select, 16=Multi select.",
    )
    required: Optional[bool] = Field(
        None,
        description="When True, this parameter must be filled in before the integration instance can be saved.",
    )
    hidden: Optional[Any] = Field(
        None,
        description="When True, this parameter is hidden from the UI. Can be a boolean or marketplace-specific value.",
    )
    options: Optional[List[str]] = Field(
        None,
        description="List of allowed values for select-type parameters (type 12 or 16). Users can only choose from these values.",
    )
    additional_info: Optional[str] = Field(
        None,
        alias="additionalinfo",
        description="Additional help text shown below the parameter in the UI. Provides extra context or instructions.",
    )
    display_password: Optional[str] = Field(
        None,
        alias="displaypassword",
        description="Display label for the password field in credential-type parameters.",
    )
    hidden_username: Optional[bool] = Field(
        None,
        alias="hiddenusername",
        description="When True, the username field is hidden in credential-type parameters.",
    )
    hidden_password: Optional[bool] = Field(
        None,
        alias="hiddenpassword",
        description="When True, the password field is hidden in credential-type parameters.",
    )
    from_license: Optional[str] = Field(
        None,
        alias="fromlicense",
        description="License field to populate this parameter from. Used for license-based authentication.",
    )


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
    name: str = Field(
        ...,
        description="Unique name of the command (e.g. 'ip', 'domain', 'get-alerts'). Used in playbooks and the CLI.",
    )
    execution: Optional[bool] = Field(
        None,
        description="When True, this command performs a write/execution action (not just read). Used for compliance and auditing.",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what this command does. Shown in the UI and used for documentation.",
    )
    deprecated: Optional[bool] = Field(
        None,
        description="When True, this command is deprecated and should not be used in new playbooks.",
    )
    system: Optional[bool] = Field(
        None,
        description="When True, this is a system-provided command that cannot be deleted.",
    )
    arguments: Optional[List[Argument]] = Field(  # type:ignore[valid-type]
        None,
        description="List of input arguments accepted by this command.",
    )
    outputs: Optional[List[IntegrationOutput]] = Field(
        None,
        description="List of output fields returned by this command. Defines the context paths populated after execution.",
    )
    important: Optional[List[Important]] = Field(  # type:ignore[valid-type]
        None,
        description="List of important outputs to highlight in the UI. These outputs are shown prominently in the war room.",
    )
    timeout: Optional[int] = Field(
        None,
        description="Command execution timeout in seconds. Overrides the integration-level timeout for this specific command.",
    )
    polling: Optional[bool] = Field(
        None,
        description="When True, this command supports polling mode for long-running operations.",
    )
    prettyname: Optional[str] = Field(
        None,
        description="Human-readable display name of the command shown in the UI.",
    )
    compliantpolicies: Optional[List[str]] = Field(
        None,
        description="List of compliance policy names this command satisfies. Used for compliance reporting.",
    )
    supportedModules: Optional[
        Annotated[
            List[PlatformSupportedModules],
            Field(min_length=1, max_length=len(PlatformSupportedModules)),
        ]
    ] = Field(
        None,
        description="Optional list of platform modules that support this command. Restricts availability to specific modules.",
    )


Command = create_model(
    model_name="Command",
    base_models=(
        _Command,
        DEPRECATED_DYNAMIC_MODEL,
        DESCRIPTION_DYNAMIC_MODEL,
        NAME_DYNAMIC_MODEL,
        QUICK_ACTION_DYNAMIC_MODEL,
        HIDDEN_DYNAMIC_MODEL,
    ),
)


class _Script(BaseStrictModel):
    script: str = Field(
        ...,
        description="The integration script code. For Python integrations, this is the Python source code. For unified integrations, this is '-'.",
    )
    type_: ScriptType = Field(
        ...,
        alias="type",
        description="Script language type. Must be one of: 'python3', 'python2', 'powershell', 'javascript'.",
    )
    docker_image: str = Field(
        None,
        alias="dockerimage",
        description="Docker image used to run this integration (e.g. 'demisto/python3:3.10.12.63474'). Must be a valid Docker image tag.",
    )
    alt_docker_images: Optional[List[str]] = Field(
        None,
        alias="alt_dockerimages",
        description="Alternative Docker images for different platforms. Used for multi-architecture support.",
    )
    native_image: Optional[List[str]] = Field(
        None,
        alias="nativeImage",
        description="Native image configurations for running without Docker. Used for native execution environments.",
    )
    is_fetch: Optional[bool] = Field(
        None,
        alias="isfetch",
        description="When True, this integration fetches incidents from the external service. Enables the fetch incidents mechanism.",
    )
    is_fetch_events: Optional[bool] = Field(
        None,
        alias="isfetchevents",
        description="When True, this integration fetches events for XSIAM. Enables the fetch events mechanism.",
    )
    is_fetch_assets: Optional[bool] = Field(
        None,
        alias="isfetchassets",
        description="When True, this integration fetches assets for XSIAM. Enables the fetch assets mechanism.",
    )
    mcp: Optional[bool] = Field(
        None,
        alias="mcp",
        description="When True, this integration supports the Model Context Protocol (MCP) for AI agent integration.",
    )
    long_running: Optional[bool] = Field(
        None,
        alias="longRunning",
        description="When True, this integration runs as a long-running process rather than per-command execution.",
    )
    long_running_port: Optional[bool] = Field(
        None,
        alias="longRunningPort",
        description="When True, the long-running integration exposes a port for incoming connections.",
    )
    is_mappable: Optional[bool] = Field(
        None,
        alias="ismappable",
        description="When True, this integration supports incident field mapping via the mapper.",
    )
    is_remote_sync_in: Optional[bool] = Field(
        None,
        alias="isremotesyncin",
        description="When True, this integration supports incoming mirroring (syncing changes from the external system to XSOAR).",
    )
    is_remote_sync_out: Optional[bool] = Field(
        None,
        alias="isremotesyncout",
        description="When True, this integration supports outgoing mirroring (syncing changes from XSOAR to the external system).",
    )
    commands: Optional[List[Command]] = Field(  # type:ignore[valid-type]
        None,
        description="List of commands provided by this integration. Each command is callable from playbooks and the CLI.",
    )
    run_once: Optional[bool] = Field(
        None,
        alias="runonce",
        description="When True, this integration runs only once and then stops. Used for one-time setup integrations.",
    )
    sub_type: Optional[str] = Field(
        [TYPE_PYTHON2, TYPE_PYTHON3],
        alias="subtype",
        description="Python sub-type. Must be 'python3' or 'python2'. Determines which Python version is used.",
    )
    feed: Optional[bool] = Field(
        None,
        description="When True, this integration is a feed integration that ingests threat intelligence indicators.",
    )
    is_fetch_samples: Optional[bool] = Field(
        None,
        alias="isFetchSamples",
        description="When True, this integration can fetch sample incidents for testing and configuration.",
    )
    reset_context: Optional[bool] = Field(
        None,
        alias="resetContext",
        description="When True, the integration context is reset on each command execution.",
    )


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


class ConditionOperator(StrEnum):
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"


class Condition(BaseStrictModel):
    name: str
    operator: ConditionOperator
    value: Optional[str] = None


class TriggerEffectAction(BaseStrictModel):
    hidden: Optional[bool] = None
    required: Optional[bool] = None


class TriggerEffect(BaseStrictModel):
    name: str
    action: TriggerEffectAction


class Trigger(BaseStrictModel):
    conditions: List[Condition]
    effects: List[TriggerEffect]


class _StrictIntegration(BaseStrictModel):
    common_fields: CommonFieldsIntegration = Field(  # type:ignore[valid-type]
        ...,
        alias="commonfields",
        description="Common metadata fields including the integration's unique ID and schema version.",
    )
    display: str = Field(
        ...,
        description="Display name of the integration shown in the UI and marketplace.",
    )
    beta: Optional[bool] = Field(
        None,
        description="When True, marks this integration as a beta release. Beta integrations may have limited support.",
    )
    category: str = Field(
        ...,
        description="Category of the integration (e.g. 'Data Enrichment & Threat Intelligence', 'Endpoint'). Must use a valid category name.",
    )
    section_order: Optional[conlist(SectionOrderValues, min_items=1, max_items=5)] = (
        Field(  # type:ignore[valid-type]
            None,
            alias="sectionorder",
            description="Ordered list of configuration sections. Allowed values: Connect, Collect, Optimize, Mirroring, Result. Max 5 sections.",
        )
    )
    configurations: List[Configuration] = Field(  # type:ignore[valid-type]
        ...,
        alias="configuration",
        description="List of configuration parameters for this integration. Defines the settings users must fill in when creating an instance.",
    )
    image: Optional[str] = Field(
        None,
        description="Base64-encoded integration logo image. Shown in the UI and marketplace.",
    )
    description: str = Field(
        ...,
        description="Short description of the integration shown in the marketplace listing.",
    )
    provider: Optional[str] = Field(
        None,
        description="Name of the technology provider (e.g. 'Palo Alto Networks', 'CrowdStrike'). Shown in the marketplace.",
    )
    default_mapper_in: Optional[str] = Field(
        None,
        alias="defaultmapperin",
        description="Name of the default incoming mapper for this integration. Applied automatically when creating an instance.",
    )
    default_mapper_out: Optional[str] = Field(
        None,
        alias="defaultmapperout",
        description="Name of the default outgoing mapper for this integration. Applied automatically when creating an instance.",
    )
    default_classifier: Optional[str] = Field(
        None,
        alias="defaultclassifier",
        description="Name of the default classifier for this integration. Applied automatically when creating an instance.",
    )
    detailed_description: Optional[str] = Field(
        None,
        alias="detaileddescription",
        description="Detailed description of the integration shown in the integration configuration panel. Supports markdown.",
    )
    auto_config_instance: Optional[bool] = Field(
        None,
        alias="autoconfiginstance",
        description="When True, an integration instance is automatically configured during pack installation.",
    )
    support_level_header: MarketplaceVersions = Field(
        None,
        alias="supportlevelheader",
        description="Marketplace version for which the support level header is shown.",
    )
    script: Script = Field(  # type:ignore[valid-type]
        ...,
        description="Script configuration block containing the integration code, commands, and execution settings.",
    )
    hidden: Optional[bool] = Field(
        None,
        description="When True, this integration is hidden from the marketplace and integration list.",
    )
    internal: Optional[bool] = Field(
        None,
        description="When True, marks this integration as internal and not intended for direct use by end users.",
    )
    source: Optional[str] = Field(
        None,
        description="Source repository or origin of this integration.",
    )
    videos: Optional[List[str]] = Field(
        None,
        description="List of URLs to demo or tutorial videos for this integration.",
    )
    versioned_fields: dict = Field(
        None,
        alias="versionedfields",
        description="Dictionary of fields that have marketplace-specific versions. Used for marketplace-specific customization.",
    )
    default_enabled: Optional[bool] = Field(
        None,
        alias="defaultEnabled",
        description="When True, the integration instance is enabled by default after installation.",
    )
    script_not_visible: Optional[bool] = Field(
        None,
        alias="scriptNotVisible",
        description="When True, the integration script code is not visible to users.",
    )
    hybrid: Optional[bool] = Field(
        None,
        description="When True, this integration supports both XSOAR and XSIAM platforms simultaneously.",
    )
    supports_quick_actions: Optional[bool] = Field(
        None,
        alias="supportsquickactions",
        description="When True, this integration supports quick actions that can be triggered from the UI.",
    )
    is_cloud_provider_integration: Optional[bool] = Field(
        False,
        alias="isCloudProviderIntegration",
        description="When True, marks this as a cloud provider integration with special handling for cloud authentication.",
    )
    triggers: Optional[List[Trigger]] = Field(
        None,
        description="List of UI triggers that dynamically show/hide configuration parameters based on other parameter values.",
    )
    supportedModules: Optional[
        Annotated[List[PlatformSupportedModules], Field(min_length=1, max_length=7)]
    ] = Field(
        None,
        description="Optional list of platform modules that support this integration. Restricts availability to specific modules.",
    )

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

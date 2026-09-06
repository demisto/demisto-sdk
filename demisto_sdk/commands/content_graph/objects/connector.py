"""Connector content item - models a unified-connectors-content connector.

A Connector is a single content item whose main file is ``connector.yaml``.
Sub-files (connection.yaml, capabilities.yaml, configurations.yaml, triggers.yaml,
summary.yaml, handler.yaml, serializer.yaml) are modeled using a hybrid approach:

* **Pydantic sub-models** for structured, queryable data (like ``Command`` / ``Parameter``
  for ``Integration``).
* **RelatedFile instances** for file-level concerns (existence, git status, path resolution).
"""

from configparser import ConfigParser
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, root_validator, validator

from demisto_sdk.commands.common.constants import CONNECTOR_IGNORE_FILE_NAME
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.common import (
    ContentType,
    Nodes,
    Relationships,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.parsers.related_files import (
    CapabilitiesRelatedFile,
    ConfigurationsRelatedFile,
    ConnectionRelatedFile,
    HandlerRelatedFile,
    SummaryRelatedFile,
    TriggersRelatedFile,
)

json = JSON_Handler()

# ============================================================
# Enums (constrained strings from the UCP schema)
#
# NOTE: These enums use ``str`` as a mixin so that instances serialize as
# their raw string value (Neo4j / JSON friendly) and compare equal to plain
# strings. Per the alignment decision, models do NOT enforce required fields
# or reject unknown enum values at parse time - UCP schema validation owns
# that. To stay tolerant of new/unknown values, parsing keeps the raw string
# on the model (the enums exist mainly for validators to reference).
# ============================================================


class FieldTypeEnum(str, Enum):
    """field.schema.json#/$defs/FieldType"""

    INPUT = "input"
    TEXT_AREA = "text_area"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    CHECKBOX_GROUP = "checkbox_group"
    TOGGLE = "toggle"
    LABEL = "label"
    SWITCH = "switch"
    FILE_UPLOAD = "file_upload"
    DURATION = "duration"


class ProfileTypeEnum(str, Enum):
    """connection.schema.json Profile.type"""

    OAUTH2_CLIENT_CREDENTIALS = "oauth2_client_credentials"
    OAUTH2_AUTHORIZATION_CODE = "oauth2_authorization_code"
    OAUTH2_JWT_BEARER = "oauth2_jwt_bearer"
    OAUTH2_REFRESH_TOKEN = "oauth2_refresh_token"
    PLAIN = "plain"
    API_KEY = "api_key"
    EXTERNAL_AUTH = "external_auth"
    PASSTHROUGH = "passthrough"


class TriggeringTypeEnum(str, Enum):
    """handler.schema.json Triggering.type"""

    ZERO_SCALE = "ZERO_SCALE"
    PUB_SUB = "PUB_SUB"


class TestConnectionTypeEnum(str, Enum):
    """handler.schema.json TestConnection.type"""

    ENDPOINT = "endpoint"
    SERVICE = "service"


class ActionTypeEnum(str, Enum):
    """handler.schema.json Action.type"""

    RESET_INTEGRATION_CONTEXT = "reset_integration_context"
    RESET_ASSETS_LAST_RUN = "reset_assets_last_run"
    RESET_INCIDENTS_LAST_RUN = "reset_incidents_last_run"
    RESET_FEED_LAST_RUN = "reset_feed_last_run"
    RESET_EVENTS_LAST_RUN = "reset_events_last_run"


class RequiredLicenseEnum(str, Enum):
    """capabilities.schema.json CapabilityConfig.required_license"""

    DATA_SECURITY = "data_security"
    AGENTIX = "agentix"
    ASM = "asm"
    CLOUD = "cloud"
    CLOUD_APPSEC = "cloud_appsec"
    CLOUD_POSTURE = "cloud_posture"
    CLOUD_RUNTIME_SECURITY = "cloud_runtime_security"
    COLD_RTN = "cold_rtn"
    COMPUTE_UNIT = "compute_unit"
    EDR = "edr"
    ENDPOINT_DLP = "endpoint_dlp"
    EPP = "epp"
    EXPOSURE_MANAGEMENT = "exposure_management"
    FORENSICS = "forensics"
    HOST_INSIGHTS = "host_insights"
    IDENTITY_THREAT = "identity_threat"
    RTN = "rtn"
    TIM = "tim"
    XDR = "xdr"
    XSIAM = "xsiam"
    XSOAR = "xsoar"


class ValidationRuleTypeEnum(str, Enum):
    """validation.schema.json ValidationRule.type"""

    PATTERN = "pattern"
    MIN_LENGTH = "minLength"
    MAX_LENGTH = "maxLength"
    ASYNC = "async"


# ============================================================
# Shared field sub-models
# ============================================================


class FieldModifiers(BaseModel):
    """field-options.schema.json#/$defs/Modifiers"""

    required: Optional[bool] = None
    hidden: Optional[bool] = None
    read_only: Optional[bool] = None


class FieldLayout(BaseModel):
    """field-options.schema.json#/$defs/FieldLayout"""

    cols: Optional[int] = None
    row_span: Optional[int] = None


class FieldOptions(BaseModel):
    """field-options.schema.json#/$defs/FieldOptions.

    All keys optional; the UCP schema enforces per-field-type constraints.
    """

    description: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
    default_value: Optional[Any] = None
    values: Optional[List[dict]] = None
    units: Optional[List[str]] = None
    output_format: Optional[str] = None
    hint: Optional[str] = None
    fluid: Optional[bool] = None
    is_number_input: Optional[bool] = None
    clearable: Optional[bool] = None
    limit: Optional[bool] = None
    searchable: Optional[bool] = None
    orientation: Optional[str] = None
    mask: Optional[bool] = None
    variant: Optional[str] = None
    mode: Optional[str] = None
    query_params: Optional[dict] = None
    formats: Optional[str] = None
    multiple: Optional[bool] = None
    file_upload_hint: Optional[str] = None
    empty_values_message: Optional[str] = None
    layout: Optional[FieldLayout] = None
    create_modifiers: Optional[FieldModifiers] = None
    edit_modifiers: Optional[FieldModifiers] = None


class FieldBehavior(BaseModel):
    """field.schema.json#/$defs/Behavior - UI-only behavior config."""

    type: Optional[str] = None  # currently only "apply"
    label: Optional[str] = None


class ValidationRule(BaseModel):
    """validation.schema.json#/$defs/ValidationRule"""

    type: Optional[str] = None  # ValidationRuleTypeEnum
    value: Optional[Any] = None  # regex string or integer
    message: Optional[str] = None
    validation_type: Optional[str] = None  # e.g. "uniqueness"
    options: Optional[dict] = None  # ValidationOptions{debounce, showLoading}


class ValidationEntry(BaseModel):
    """validation.schema.json#/$defs/ValidationEntry - trigger-grouped rules."""

    trigger: Optional[str] = None  # "change" | "blur"
    rules: List[ValidationRule] = []


class CheckboxGroupItemOptions(BaseModel):
    """field.schema.json#/$defs/CheckboxGroupItemOptions"""

    description: Optional[str] = None
    create_modifiers: Optional[FieldModifiers] = None
    edit_modifiers: Optional[FieldModifiers] = None


class CheckboxGroupItem(BaseModel):
    """field.schema.json#/$defs/CheckboxGroupItem"""

    id: str
    title: Optional[str] = None
    options: Optional[CheckboxGroupItemOptions] = None


class ConnectorField(BaseModel):
    """A single field definition used across connection, capabilities, and configurations.

    Mirrors ``field.schema.json#/$defs/Field``. ``field_type`` is kept as a
    plain string (values come from :class:`FieldTypeEnum`) so unknown/new
    types don't break parsing.
    """

    id: str
    title: Optional[str] = None
    field_type: Optional[str] = None  # FieldTypeEnum values
    metadata: Optional[dict] = None  # FieldMetadata (free-form, platform+handler keys)
    options: Optional[FieldOptions] = None
    validations: Optional[List[ValidationEntry]] = None
    behavior: Optional[FieldBehavior] = None
    # Checkbox items for checkbox_group fields.
    fields: Optional[List[CheckboxGroupItem]] = None


class FieldGroup(BaseModel):
    """field.schema.json#/$defs/FieldGroup - a row of fields."""

    fields: List[ConnectorField] = []
    view_group: Optional[str] = None  # grouped connectors only
    required_for_capabilities: Optional[List[str]] = None
    advanced: Optional[bool] = None


class ViewGroup(BaseModel):
    """A view-group (tile) registry entry from connection.yaml / configurations.yaml."""

    id: str
    label: Optional[str] = None
    help_text: Optional[str] = None


class GeneralConfigurations(BaseModel):
    description: Optional[str] = None
    configurations: List[FieldGroup] = []


# ============================================================
# Connector identity - from connector.yaml
# ============================================================


class ConnectorOwnership(BaseModel):
    team: Optional[str] = None
    maintainers: List[str] = []


class ConnectorMetadata(BaseModel):
    """connector.schema.json metadata block.

    Kept permissive (optional fields) - the UCP schema enforces required
    fields (title, description, version, categories, vendor, publisher,
    ownership).
    """

    title: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None  # semver e.g. "1.0.0"
    categories: List[str] = []  # classification categories
    tags: List[str] = []
    domain: Optional[str] = None
    vendor: Optional[str] = None
    publisher: Optional[str] = None
    author_image: Optional[str] = None
    documentation: Optional[str] = None  # URL to external docs
    is_recommended: bool = False
    ownership: ConnectorOwnership = ConnectorOwnership()


class ConnectorSettings(BaseModel):
    """connector.schema.json settings block."""

    allow_skip_verification: Optional[bool] = None
    skip_cut_off_check: Optional[bool] = None
    required_features: List[str] = []
    grouped: bool = False


# ============================================================
# Connection data - parsed from connection.yaml
# ============================================================


class ProfileOptions(BaseModel):
    """connection.schema.json#/$defs/ProfileOptions"""

    use_base64_header: Optional[bool] = None
    allow_scopes: Optional[bool] = None
    default_token_expiry: Optional[int] = None


class VaultMappingFields(BaseModel):
    """connection.schema.json VaultMapping.map"""

    user: Optional[str] = None
    password: Optional[str] = None
    sshkey: Optional[str] = None


class VaultMapping(BaseModel):
    """connection.schema.json#/$defs/VaultMapping - passthrough profiles only."""

    id: str
    map: Optional[VaultMappingFields] = None


class ConnectionProfile(BaseModel):
    """An authentication profile from connection.yaml."""

    id: str  # e.g. "oauth2_client_credentials.identity"
    type: Optional[str] = None  # ProfileTypeEnum values
    title: Optional[str] = None
    description: Optional[str] = None
    view_group: Optional[str] = None  # grouped connectors only
    vault_support: Optional[bool] = None
    vault_mappings: List[VaultMapping] = []
    discovery_url: Optional[str] = None
    token_endpoint: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token_scope: Optional[str] = None
    options: Optional[ProfileOptions] = None
    # Handler-namespaced free-form profile metadata (keyed by module name).
    metadata: Optional[dict] = None
    configurations: List[FieldGroup] = []


class ConnectorConnectionData(BaseModel):
    """Parsed structured data from connection.yaml."""

    title: Optional[str] = None
    description: Optional[str] = None
    help: Optional[str] = None
    view_groups: List[ViewGroup] = []
    general_configurations: Optional[GeneralConfigurations] = None
    profiles: List[ConnectionProfile] = []


# ============================================================
# Capability data - parsed from capabilities.yaml
# ============================================================


class ConnectorCapabilitiesData(BaseModel):
    """Parsed metadata block from capabilities.yaml.

    Mirrors ``ConnectorConnectionData`` but only carries the file-level
    ``metadata`` block (title/description/help) and the file-level
    ``general_configurations`` block. The individual capability items live on
    ``Connector.capabilities`` (``List[CapabilityData]``).
    """

    title: Optional[str] = None
    description: Optional[str] = None
    help: Optional[str] = None
    general_configurations: Optional[GeneralConfigurations] = None


class LabelTooltip(BaseModel):
    """capabilities.schema.json Labels object-form tooltip."""

    id: str
    params: Optional[Dict[str, str]] = None


class Label(BaseModel):
    """Object form of a capability label: ``{id, tooltip?}``.

    Labels may also be plain strings; parsing normalizes both forms into a
    ``List[Label]`` where the string form is stored under ``id``.
    """

    id: str
    tooltip: Optional[LabelTooltip] = None


class CapabilityConfig(BaseModel):
    """capabilities.schema.json#/$defs/CapabilityConfig"""

    required_license: List[str] = []  # RequiredLicenseEnum values
    required_features: List[str] = []


class SubCapability(BaseModel):
    id: str
    title: Optional[str] = None
    default_enabled: bool = False
    required: bool = False
    read_only: bool = False
    labels: List[Label] = []
    config: Optional[CapabilityConfig] = None
    # Effective license list: own value, or inherited from parent capability
    # (populated by the parser).
    required_license: List[str] = []


class CapabilityData(BaseModel):
    """A single capability from capabilities.yaml.

    The ``configurations`` field contains the **unified** list of field groups:
    general_configurations from capabilities.yaml + general_configurations from
    configurations.yaml + per-capability configurations from configurations.yaml.
    """

    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    default_enabled: bool = False
    required: bool = False
    read_only: bool = False
    labels: List[Label] = []
    config: Optional[CapabilityConfig] = None
    sub_capabilities: List[SubCapability] = []
    # Multi-service connector fields.
    is_global: bool = Field(default=False, alias="global")
    partial: bool = False
    author_image: Optional[str] = None
    global_message: Optional[str] = None
    service_ids: List[str] = []
    configurations: List[FieldGroup] = []  # unified: general + per-capability configs

    class Config:
        allow_population_by_field_name = True


# ============================================================
# Serializer data - parsed from serializer.yaml
# (defined before HandlerData to avoid forward references)
# ============================================================


class FieldMapping(BaseModel):
    """Raw serializer entry from serializer.yaml (SerializerEntry).

    The schema requires only ``id`` and at least one of ``field_name`` /
    ``field_value``, so ``field_name`` is optional here (transform-only
    entries omit it).
    """

    id: str  # connector field ID (connector_param_name)
    # Target field name for the handler (rename). Optional for transform-only
    # entries.
    field_name: Optional[str] = None
    field_value: Optional[str] = None  # optional value transform (e.g. "toString")


class ComputedCondition(BaseModel):
    """serializer.schema.json#/$defs/Condition"""

    type: Optional[str] = None  # "capability" | "field"
    options: Optional[dict] = None  # CapabilityOptions | FieldConditionOptions


class ComputedConditionGroup(BaseModel):
    """serializer.schema.json#/$defs/ConditionGroup (AND logic within group)."""

    conditions: List[ComputedCondition] = []


class ComputedOutput(BaseModel):
    """serializer.schema.json#/$defs/ComputedOutput"""

    id: str
    value: Optional[Any] = None


class ComputedFieldRule(BaseModel):
    """serializer.schema.json#/$defs/ComputedFieldRule."""

    output: List[ComputedOutput] = []
    any_of: List[ComputedConditionGroup] = []  # OR logic across groups


class SerializerData(BaseModel):
    field_mappings: List[FieldMapping] = []
    computed_fields: List[ComputedFieldRule] = []


# ============================================================
# Resolved parameter mapping
# (defined before HandlerData to avoid forward references)
# ============================================================


class ResolvedParamMapping(BaseModel):
    """Resolved parameter mapping for a handler.

    Maps connector field IDs to integration parameter names.
    If a field appears in the serializer, the names differ.
    If not, both names equal the field ID.
    """

    connector_param_name: str  # field ID in connector YAML (e.g. "domain")
    content_param_name: str  # param name in integration YAML (e.g. "InstanceURL")
    field_value_transform: Optional[str] = None  # optional value transform
    is_serialized: bool = False  # True if mapping came from serializer.yaml
    source_file: str = ""  # which connector file defines this field


# ============================================================
# Handler data - parsed from components/handlers/<name>/handler.yaml
# ============================================================


class HandlerOwnership(BaseModel):
    """Ownership info from handler metadata."""

    team: str = ""
    maintainers: List[str] = []


class HandlerMetadata(BaseModel):
    """Typed metadata from a handler.yaml ``metadata`` block."""

    # Schema allows string OR number for version.
    version: Optional[Union[str, float, int]] = None
    description: str = ""
    module: Optional[str] = None
    tags: List[str] = []
    labels: Optional[dict] = None  # handler-specific metadata labels
    ownership: HandlerOwnership = HandlerOwnership()


class HandlerTriggering(BaseModel):
    type: Optional[str] = None  # TriggeringTypeEnum: "ZERO_SCALE" | "PUB_SUB"
    labels: Optional[Dict[str, str]] = None
    args: Optional[dict] = None


class HandlerAuthMethod(BaseModel):
    """Object form of an auth_options[].methods[] entry."""

    id: str
    scopes: List[str] = []


class HandlerAuthOption(BaseModel):
    id: str  # references connection profile ID
    scopes: List[str] = []
    workloads: List[str] = []
    # Schema allows each method to be a string OR an object {id, scopes[]}.
    methods: List[Union[str, HandlerAuthMethod]] = []


class HandlerAction(BaseModel):
    """handler.schema.json#/$defs/Action."""

    type: Optional[str] = None  # ActionTypeEnum
    display: Optional[str] = None
    description: Optional[str] = None


class HandlerCapability(BaseModel):
    id: str  # references capability ID
    # "none" for the anonymous shape; mutually exclusive with auth_options.
    auth: Optional[str] = None
    auth_options: List[HandlerAuthOption] = []
    # Capability-level workloads (only for the anonymous auth: "none" shape).
    workloads: List[str] = []
    actions: List[HandlerAction] = []


class HandlerTestConnection(BaseModel):
    type: Optional[str] = None  # TestConnectionTypeEnum: "endpoint" | "service"
    host: Optional[str] = None
    service: Optional[str] = None
    endpoint: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class HandlerData(BaseModel):
    """Parsed structured data from a handler.yaml file."""

    id: str
    metadata: HandlerMetadata = HandlerMetadata()
    enabled: bool = True
    triggering: HandlerTriggering = HandlerTriggering()
    capabilities: List[HandlerCapability] = []
    test_connection: HandlerTestConnection = HandlerTestConnection()
    # Metro (multi-tenant) override for connection testing.
    test_connection_metro: Optional[HandlerTestConnection] = None
    serializer: Optional[SerializerData] = None
    # Multi-service connector fields (mutually exclusive per schema).
    service_ids: List[str] = []
    is_general: bool = False
    handler_dir_name: str  # directory name for path resolution
    resolved_params: List[ResolvedParamMapping] = []  # built by parser

    # Cross-link to matched Integration (set by ConnectorAwareInitializer)
    related_integration: Optional[Any] = None

    # Absolute path to the owning connector's root directory. Stamped by the
    # parent ``Connector`` (see ``_stamp_handler_paths``) so a handler can
    # resolve its own on-disk ``handler.yaml`` without the caller needing to
    # know the connector layout. Reusable by every handler-level validator.
    connector_path: Optional[Path] = None

    @property
    def file_path(self) -> Optional[Path]:
        """Absolute path to this handler's ``handler.yaml``.

        Returns ``None`` when the owning connector's path is unknown (e.g. a
        handler constructed in isolation). Mirrors ``HandlerRelatedFile``'s
        ``<connector>/components/handlers/<dir>/handler.yaml`` layout.
        """
        if self.connector_path is None:
            return None
        return (
            self.connector_path
            / "components"
            / "handlers"
            / self.handler_dir_name
            / "handler.yaml"
        )

    @property
    def module(self) -> Optional[str]:
        return self.metadata.module

    @property
    def team(self) -> str:
        return self.metadata.ownership.team

    @property
    def is_xsoar(self) -> bool:
        """Identify if this handler is XSOAR-related."""
        return (
            self.module == "xsoar"
            or self.team == "xsoar"
            or "@xsoar-content" in (self.metadata.ownership.maintainers or [])
        )

    @property
    def xsoar_integration_id(self) -> Optional[str]:
        if self.triggering.labels:
            return self.triggering.labels.get("xsoar-integration-id")
        return None

    @property
    def xsoar_pack_id(self) -> Optional[str]:
        if self.triggering.labels:
            return self.triggering.labels.get("xsoar-pack-id")
        return None


# ============================================================
# Capability-handler mapping
# ============================================================


class CapabilityHandlerMapping(BaseModel):
    """Links a capability to the handler(s) that serve it.

    Built by the parser from the cross-reference between capabilities.yaml
    and each handler's ``capabilities`` list.  For example, if capability
    ``"identity-posture"`` is served by handlers ``["xsoar", "cwp"]``, this
    mapping records that relationship along with auth and config metadata.

    Used by validators to look up which handlers back a capability and
    whether the capability has XSOAR involvement.
    """

    capability_id: str  # matches CapabilityData.id
    handler_ids: List[str] = []  # handler IDs that declare this capability
    is_xsoar: bool = False  # True if at least one handler is XSOAR-related
    auth_profile_ids: List[
        str
    ] = []  # connection profile IDs referenced by auth_options
    has_configurations: bool = (
        False  # True if configurations.yaml has a section for this capability
    )


# ============================================================
# Connector content item
# ============================================================


class Connector(ContentItem, content_type=ContentType.CONNECTOR):  # type: ignore[call-arg]
    """A unified connector content item.

    Uses a hybrid approach:
    - Pydantic sub-models for structured, queryable data
    - RelatedFile instances for file-level concerns
    """

    # === Fields from connector.yaml ===
    enabled: bool = True
    connector_metadata: ConnectorMetadata = Field(alias="metadata")
    settings: Optional[ConnectorSettings] = None

    @root_validator(pre=True)
    def _rebuild_nested_from_neo4j(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct nested sub-models when loading a Connector from Neo4j.

        ``to_dict`` flattens ``ConnectorMetadata`` and ``ConnectorSettings`` so
        they can be stored as primitive node properties (Neo4j rejects nested
        maps). To make the round-trip work, ``to_dict`` ALSO stores the full
        original sub-structures as JSON strings under ``metadata_json`` /
        ``settings_json``. This validator decodes those strings back into
        the nested dicts (under the original aliases ``metadata`` /
        ``settings``) before normal pydantic validation runs - so
        ``Connector.parse_obj(node_props)`` succeeds even though the raw
        Neo4j node has no ``metadata`` key.

        If the JSON strings are absent (e.g. a freshly-parsed yaml object,
        or an old node written before this change), the values dict is
        returned unchanged and pydantic falls through to its normal path.
        Pre=True root validators receive a plain dict, so this runs before
        any per-field validation.
        """
        if not isinstance(values, dict):
            return values

        # metadata: prefer JSON round-trip, else fall back to flattened scalars.
        if "metadata" not in values and values.get("connector_metadata") is None:
            metadata_json = values.pop("metadata_json", None)
            if isinstance(metadata_json, str):
                try:
                    values["metadata"] = json.loads(metadata_json)
                except (ValueError, TypeError):
                    # Intentionally ignore malformed/non-JSON metadata here and
                    # fall back to reconstruction from flattened scalar fields.
                    pass
            if "metadata" not in values:
                # Last-resort reconstruction from the flattened scalars that
                # to_dict promoted. This keeps old nodes parseable too.
                rebuilt: Dict[str, Any] = {}
                for key in (
                    "title",
                    "description",
                    "version",
                    "categories",
                    "vendor",
                    "publisher",
                    "domain",
                    "author_image",
                    "documentation",
                    "is_recommended",
                    "tags",
                ):
                    if key in values:
                        rebuilt[key] = values[key]
                team = values.get("ownership_team")
                maintainers = values.get("ownership_maintainers")
                if team is not None or maintainers is not None:
                    rebuilt["ownership"] = {
                        "team": team or "",
                        "maintainers": list(maintainers or []),
                    }
                # Only inject if we found *something* worth rebuilding.
                if rebuilt:
                    values["metadata"] = rebuilt

        # settings: same pattern, but optional, so absence is fine.
        if "settings" not in values:
            settings_json = values.pop("settings_json", None)
            if isinstance(settings_json, str):
                try:
                    values["settings"] = json.loads(settings_json)
                except (ValueError, TypeError):
                    # Intentionally ignore malformed/non-JSON settings and keep
                    # the field unset so optional/fallback logic can proceed.
                    pass
            else:
                # Last-resort reconstruction from flattened scalar settings.
                rebuilt_settings: Dict[str, Any] = {}
                for key in (
                    "allow_skip_verification",
                    "skip_cut_off_check",
                    "grouped",
                    "required_features",
                ):
                    if key in values:
                        rebuilt_settings[key] = values[key]
                if rebuilt_settings:
                    values["settings"] = rebuilt_settings

        return values

    # === Parsed sub-models (populated by parser, excluded from serialization) ===
    connection: Optional[ConnectorConnectionData] = Field(None, exclude=True)
    capabilities_metadata: Optional[ConnectorCapabilitiesData] = Field(
        None, exclude=True
    )
    capabilities: List[CapabilityData] = Field(default_factory=list, exclude=True)
    handlers: List[HandlerData] = Field(default_factory=list, exclude=True)
    capability_handler_map: Dict[str, CapabilityHandlerMapping] = Field(
        default_factory=dict, exclude=True
    )
    # Relationships collected by the parser (REFERENCES_INTEGRATION / REFERENCES_PACK).
    # Excluded from serialization; consumed by the graph builder.
    relationships: Relationships = Field(default_factory=Relationships, exclude=True)

    def to_nodes(self) -> Nodes:
        """Return a ``Nodes`` collection containing this connector's graph node.

        Connectors are top-level content items (not contained in a Pack), so
        unlike :py:meth:`Pack.to_nodes` we only emit a single node.
        """
        return Nodes(self.to_dict())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the connector to a Neo4j-safe property dict.

        Neo4j only accepts primitive values (or arrays of primitives) as node
        properties - it rejects nested maps. The base implementation expands
        Pydantic sub-models (``ConnectorMetadata``, ``ConnectorSettings``)
        into nested dicts, which causes ``Neo.ClientError.Statement.TypeError``
        at node creation time.

        We flatten the structured sub-models into Neo4j-friendly scalars:

        * ``connector_metadata`` → individual top-level properties (``title``,
          ``description``, ``version``, ``vendor``, ``publisher``,
          ``domain``, ``author_image``) plus ``categories`` and ``tags`` (lists
          of strings) and ``ownership_team`` / ``ownership_maintainers``
          (flattened ownership).
        * ``settings`` → ``allow_skip_verification`` as a top-level boolean.

        The original nested attributes remain available on the live Python
        object for code that consumes them directly (e.g. reading
        ``connector.connector_metadata.ownership.maintainers``); only the
        graph-node representation is flattened.
        """
        json_dct = super().to_dict()

        # Drop the nested BaseModel dumps that Neo4j cannot store.
        metadata = json_dct.pop("metadata", None) or json_dct.pop(
            "connector_metadata", None
        )
        settings = json_dct.pop("settings", None)

        if isinstance(metadata, dict):
            # Promote primitive metadata fields to top-level node properties.
            for key in (
                "title",
                "description",
                "version",
                "vendor",
                "publisher",
                "domain",
                "author_image",
                "documentation",
                "is_recommended",
            ):
                value = metadata.get(key)
                if value is not None:
                    json_dct.setdefault(key, value)
            categories = metadata.get("categories")
            if isinstance(categories, list):
                # Neo4j accepts arrays of primitives - keep only strings.
                json_dct["categories"] = [c for c in categories if isinstance(c, str)]
            tags = metadata.get("tags")
            if isinstance(tags, list):
                # Neo4j accepts arrays of primitives - keep only strings.
                json_dct["tags"] = [t for t in tags if isinstance(t, str)]
            ownership = metadata.get("ownership")
            if isinstance(ownership, dict):
                team = ownership.get("team")
                if isinstance(team, str):
                    json_dct["ownership_team"] = team
                maintainers = ownership.get("maintainers")
                if isinstance(maintainers, list):
                    json_dct["ownership_maintainers"] = [
                        m for m in maintainers if isinstance(m, str)
                    ]

        if isinstance(settings, dict):
            for key in (
                "allow_skip_verification",
                "skip_cut_off_check",
                "grouped",
            ):
                value = settings.get(key)
                if isinstance(value, bool):
                    json_dct[key] = value
            required_features = settings.get("required_features")
            if isinstance(required_features, list):
                json_dct["required_features"] = [
                    f for f in required_features if isinstance(f, str)
                ]

        # Store the original nested structures as JSON strings so the
        # round-trip in _rebuild_nested_from_neo4j can reconstruct them
        # exactly when this node is later read back via Connector.parse_obj
        # (used by the graph search path in neo4j_graph.py). Neo4j accepts
        # strings as property values, so this is safe to store.
        if isinstance(metadata, dict):
            try:
                json_dct["metadata_json"] = json.dumps(metadata, sort_keys=True)
            except (TypeError, ValueError):
                # Non-serializable metadata is unusual; skip rather than break
                # the whole write - the flattened scalars still provide enough
                # for the reconstruction fallback in _rebuild_nested_from_neo4j.
                pass
        if isinstance(settings, dict):
            try:
                json_dct["settings_json"] = json.dumps(settings, sort_keys=True)
            except (TypeError, ValueError):
                # Non-serializable settings should not break connector writes;
                # keep flattened scalar settings (if any) and continue.
                pass

        return json_dct

    # === Derived properties ===

    @property
    def xsoar_handlers(self) -> List[HandlerData]:
        """All handlers that are XSOAR-related."""
        return [h for h in self.handlers if h.is_xsoar]

    @property
    def xsoar_capabilities(self) -> List[str]:
        """Capability IDs served by XSOAR handlers."""
        return [
            cap_id
            for cap_id, mapping in self.capability_handler_map.items()
            if mapping.is_xsoar
        ]

    @cached_property
    def capability_by_id(self) -> Dict[str, "CapabilityData"]:
        """Lookup dict mapping capability ID to CapabilityData."""
        return {c.id: c for c in self.capabilities}

    @property
    def all_connection_profile_ids(self) -> List[str]:
        return [p.id for p in (self.connection.profiles if self.connection else [])]

    # === Path resolution ===

    @validator("path", always=True)
    def validate_path(cls, v: Path, values) -> Path:
        """Resolve the connector's path to its real on-disk location.

        The base :class:`ContentItem` validator re-bases *relative* paths onto
        the content repo (``CONTENT_PATH.with_name(source_repo)``). That is
        wrong for connectors: they live in the **separate**
        unified-connectors-content (UCP) repo, not under ``content/``. Blindly
        rebasing makes ``self.path`` point at ``content/connectors/<name>``,
        which does not exist on disk - so file-level lookups such as
        ``.connector-ignore`` silently resolve to nothing.

        Resolution order:

        1. Absolute paths are trusted as-is (matches base behavior).
        2. A relative path is resolved against the current working directory
           (during discovery the CWD is the real repo root). If that resolves
           to an existing connector directory (contains ``connector.yaml``),
           use it - this correctly anchors on the UCP repo.
        3. Otherwise fall back to the base ``ContentItem`` behavior so classic
           content resolution is unchanged.
        """
        if v.is_absolute():
            return v

        cwd_candidate = (Path.cwd() / v).resolve()
        if (cwd_candidate / "connector.yaml").exists():
            return cwd_candidate

        # Fall back to the classic content-repo rebasing.
        from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH

        if not CONTENT_PATH.name:
            return CONTENT_PATH / v
        return CONTENT_PATH.with_name(values.get("source_repo", "content")) / v

    @root_validator(skip_on_failure=True)
    def _stamp_handler_paths(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Back-reference the connector's resolved path onto each handler.

        Runs after field validation so ``path`` is already resolved by
        ``validate_path``. This lets any handler-level validator use
        ``handler.file_path`` to locate its ``handler.yaml`` without knowing
        the connector directory layout.
        """
        connector_path = values.get("path")
        if connector_path is not None:
            for handler in values.get("handlers") or []:
                handler.connector_path = connector_path
        return values

    # === Ignored errors overrides ===

    @property
    def ignored_errors(self) -> List[str]:
        """Ignored error codes for the connector's main file (``connector.yaml``).

        Overrides :class:`ContentItem` so it does NOT call
        ``get_relative_path(self.path, CONTENT_PATH)`` - connectors live in a
        separate repo, so that relativization raises ``ValueError``. The
        connector ignore scheme keys the main file by its bare filename and
        :meth:`get_ignored_errors` returns ``[]`` when no ``.connector-ignore``
        exists, so a missing file is handled gracefully.
        """
        return self.get_ignored_errors("connector.yaml")

    def ignored_errors_related_files(self, file_path: Path) -> List[str]:
        """Ignored error codes for a connector sub-file, keyed by bare filename.

        Like :attr:`ignored_errors`, this avoids ``CONTENT_PATH`` relativization
        and gracefully returns ``[]`` when the ignore file is absent.
        """
        return self.get_ignored_errors(Path(file_path).name)

    def _relativize_external_path(self, absolute_path: Path) -> str:
        """Relativize a connector path against the UCP repo root.

        Connectors live in the separate unified-connectors-content repo, so
        their absolute ``path`` is not under ``CONTENT_PATH``. Keep the
        ``connectors/<name>`` tail so the serialized value is stable and
        repo-relative rather than filesystem-absolute.
        """
        parts = absolute_path.parts
        if "connectors" in parts:
            idx = parts.index("connectors")
            return Path(*parts[idx:]).as_posix()
        return super()._relativize_external_path(absolute_path)

    # === Ignored errors (.connector-ignore) ===

    def _resolve_ignore_path(self) -> Optional[Path]:
        """Locate the connector's ``.connector-ignore`` file on disk.

        ``self.path`` should already point at the real connector directory
        (see :meth:`validate_path`), but as a defensive fallback - e.g. when a
        connector is reconstructed from the Neo4j graph where ``path`` may have
        been re-based onto the content repo - we also probe a CWD-anchored
        candidate. Returns the first existing candidate, or ``None``.
        """
        candidates = [self.path / CONNECTOR_IGNORE_FILE_NAME]

        # CWD-anchored fallback using the connectors/<name> tail of the path,
        # which survives content-repo re-basing.
        parts = self.path.parts
        if "connectors" in parts:
            idx = parts.index("connectors")
            tail = Path(*parts[idx:])
            candidates.append((Path.cwd() / tail / CONNECTOR_IGNORE_FILE_NAME))

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    @cached_property
    def ignored_errors_dict(self) -> Dict[str, Dict[str, str]]:
        """Parse the connector's ``.connector-ignore`` file.

        The file is an INI-style config living at the connector root
        (sibling of ``connector.yaml``). Each section is keyed by a
        ``file:<relative-path>`` header, for example::

            [file:capabilities.yaml]
            ignore=BA127,ST111

            [file:xsoar-zoom-feed/handler.yaml]
            ignore=BA127

            [file:xsoar-zoom_iam/serializer.yaml]
            ignore=BA127

        Sub-files (connection.yaml, capabilities.yaml, ...) are keyed by
        their bare filename, while handler / serializer files are keyed by
        ``<handler_dir_name>/handler.yaml`` and
        ``<handler_dir_name>/serializer.yaml`` respectively.

        Returns an empty dict when the file does not exist (graceful
        fallback) or cannot be parsed.
        """
        ignore_path = self._resolve_ignore_path()
        result: Dict[str, Dict[str, str]] = {}
        if ignore_path is None or not ignore_path.exists():
            return result
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(ignore_path)
            for section in config.sections():
                result[section] = dict(config[section])
        except Exception:
            logger.debug(
                f"Failed to parse {CONNECTOR_IGNORE_FILE_NAME} for {self.object_id}"
            )
            return {}
        return result

    def get_ignored_errors(self, file_key: Union[str, Path]) -> List[str]:
        """Return the list of ignored error codes for a given ``.connector-ignore`` file key.

        Args:
            file_key: The relative file key used in the ignore section header
                (without the ``file:`` prefix), e.g. ``capabilities.yaml`` or
                ``xsoar-zoom-feed/handler.yaml``.

        Returns:
            A list of ignored error codes (empty if none / not found).
        """
        section = self.ignored_errors_dict.get(f"file:{file_key}")
        if not section:
            return []
        ignore_value = section.get("ignore")
        if not ignore_value:
            return []
        return [code.strip() for code in ignore_value.split(",") if code.strip()]

    @staticmethod
    def resolve_handler_ignore_key(file_path: Optional[Path]) -> Optional[str]:
        """Map a handler/serializer file path to its ``.connector-ignore`` key.

        Handler/serializer validators emit one result per handler whose ``path``
        points at ``.../components/handlers/<folder_name>/handler.yaml`` or
        ``.../serializer.yaml``. The matching ``.connector-ignore`` section is
        keyed by ``<folder_name>/handler.yaml`` / ``<folder_name>/serializer.yaml``
        (see :meth:`ignored_errors_dict`). This resolves that key from the path.

        Returns ``None`` when the path is not a connector handler/serializer file.
        """
        if file_path is None:
            return None
        filename = file_path.name
        if filename not in ("handler.yaml", "serializer.yaml"):
            return None
        parent = file_path.parent
        if parent is None or not parent.name:
            return None
        return f"{parent.name}/{filename}"

    def is_handler_error_ignored(
        self, error_code: str, file_path: Optional[Path]
    ) -> bool:
        """Whether ``error_code`` is ignored for a specific handler/serializer file.

        Resolves the ``<folder_name>/handler.yaml`` / ``<folder_name>/serializer.yaml``
        key from ``file_path`` and looks it up in the connector's
        ``.connector-ignore``. Returns ``False`` when ``file_path`` is not a
        handler/serializer file. Missing ignore files are handled gracefully
        (``get_ignored_errors`` returns ``[]``).
        """
        ignore_key = self.resolve_handler_ignore_key(file_path)
        if ignore_key is None:
            return False
        return error_code in self.get_ignored_errors(ignore_key)

    # === RelatedFile cached properties ===

    @cached_property
    def connection_file(self) -> ConnectionRelatedFile:
        return ConnectionRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def capabilities_file(self) -> CapabilitiesRelatedFile:
        return CapabilitiesRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def configurations_file(self) -> ConfigurationsRelatedFile:
        return ConfigurationsRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def triggers_file(self) -> TriggersRelatedFile:
        return TriggersRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def summary_file(self) -> SummaryRelatedFile:
        return SummaryRelatedFile(self.path, git_sha=self.git_sha)

    @cached_property
    def handler_files(self) -> List[HandlerRelatedFile]:
        """Discover and return all handler related files."""
        handlers_dir = self.path / "components" / "handlers"
        result: List[HandlerRelatedFile] = []
        if handlers_dir.exists():
            for handler_dir in sorted(handlers_dir.iterdir()):
                if handler_dir.is_dir():
                    h = HandlerRelatedFile(
                        self.path, handler_dir.name, git_sha=self.git_sha
                    )
                    if h.exist:
                        result.append(h)
        return result

    @staticmethod
    def match(_dict: dict, path: Path) -> bool:
        """Check if the given path/dict represents a Connector content item."""
        return path.name == "connector.yaml" and "connectors" in path.parts

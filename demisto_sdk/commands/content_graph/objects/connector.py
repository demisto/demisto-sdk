"""Connector content item — models a unified-connectors-content connector.

A Connector is a single content item whose main file is ``connector.yaml``.
Sub-files (connection.yaml, capabilities.yaml, configurations.yaml, triggers.yaml,
summary.yaml, handler.yaml, serializer.yaml) are modeled using a hybrid approach:

* **Pydantic sub-models** for structured, queryable data (like ``Command`` / ``Parameter``
  for ``Integration``).
* **RelatedFile instances** for file-level concerns (existence, git status, path resolution).
"""

from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.parsers.related_files import (
    CapabilitiesRelatedFile,
    ConfigurationsRelatedFile,
    ConnectionRelatedFile,
    HandlerRelatedFile,
    SummaryRelatedFile,
    TriggersRelatedFile,
)

# ============================================================
# Shared field sub-models
# ============================================================


class FieldModifiers(BaseModel):
    required: bool = False
    disabled: bool = False
    hidden: bool = False
    read_only: bool = False


class FieldOptions(BaseModel):
    mask: Optional[bool] = None
    placeholder: Optional[str] = None
    description: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[Any] = None
    hint: Optional[str] = None
    values: Optional[List[dict]] = None
    layout: Optional[dict] = None
    create_modifiers: Optional[FieldModifiers] = None
    edit_modifiers: Optional[FieldModifiers] = None


class ConnectorField(BaseModel):
    """A single field definition used across connection, capabilities, and configurations."""

    id: str
    title: str
    field_type: str  # "input", "select", "checkbox", "switch"
    metadata: Optional[dict] = None
    options: Optional[FieldOptions] = None
    validations: Optional[List[dict]] = None
    behavior: Optional[dict] = None


class FieldGroup(BaseModel):
    fields: List[ConnectorField]


class GeneralConfigurations(BaseModel):
    description: Optional[str] = None
    configurations: List[FieldGroup] = []


# ============================================================
# Connector identity — from connector.yaml
# ============================================================


class ConnectorOwnership(BaseModel):
    team: str
    maintainers: List[str] = []


class ConnectorMetadata(BaseModel):
    title: str
    description: str
    version: str  # semver e.g. "1.0.0"
    category: str
    tags: List[str] = []
    domain: Optional[str] = None
    vendor: str
    publisher: str
    author_image: Optional[str] = None
    ownership: ConnectorOwnership


class ConnectorSettings(BaseModel):
    allow_skip_verification: bool = False


# ============================================================
# Connection data — parsed from connection.yaml
# ============================================================


class ConnectionProfile(BaseModel):
    """An authentication profile from connection.yaml."""

    id: str  # e.g. "oauth2_client_credentials.identity"
    type: str  # "oauth2_client_credentials", "plain", "api_key", etc.
    title: str
    description: Optional[str] = None
    discovery_url: Optional[str] = None
    token_endpoint: Optional[str] = None
    authorization_endpoint: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token_scope: Optional[str] = None
    options: Optional[dict] = None
    configurations: List[FieldGroup] = []


class ConnectorConnectionData(BaseModel):
    """Parsed structured data from connection.yaml."""

    title: str
    description: str
    help: Optional[str] = None
    general_configurations: Optional[GeneralConfigurations] = None
    profiles: List[ConnectionProfile] = []


# ============================================================
# Capability data — parsed from capabilities.yaml
# ============================================================


class SubCapability(BaseModel):
    id: str
    title: str
    default_enabled: bool = False
    required: bool = False
    required_license: List[str] = []  # own value, or inherited from parent capability


class CapabilityConfig(BaseModel):
    required_license: List[str] = []


class CapabilityData(BaseModel):
    """A single capability from capabilities.yaml.

    The ``configurations`` field contains the **unified** list of field groups:
    general_configurations from capabilities.yaml + general_configurations from
    configurations.yaml + per-capability configurations from configurations.yaml.
    """

    id: str
    title: str
    description: str
    default_enabled: bool = False
    required: bool = False
    labels: List[str] = []
    config: Optional[CapabilityConfig] = None
    sub_capabilities: List[SubCapability] = []
    configurations: List[FieldGroup] = []  # unified: general + per-capability configs


# ============================================================
# Serializer data — parsed from serializer.yaml
# (defined before HandlerData to avoid forward references)
# ============================================================


class FieldMapping(BaseModel):
    """Raw serializer entry from serializer.yaml."""

    id: str  # connector field ID (connector_param_name)
    field_name: str  # integration parameter name (content_param_name)
    field_value: Optional[str] = None  # optional value transform (e.g. "toString")


class ComputedFieldRule(BaseModel):
    output: List[dict]
    any_of: List[dict] = []


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
# Handler data — parsed from components/handlers/<name>/handler.yaml
# ============================================================


class HandlerTriggering(BaseModel):
    type: str  # "ZERO_SCALE" or "PUB_SUB"
    labels: Optional[Dict[str, str]] = None
    args: Optional[dict] = None


class HandlerAuthOption(BaseModel):
    id: str  # references connection profile ID
    scopes: List[str] = []
    workloads: List[str] = []
    methods: Optional[List[Any]] = None


class HandlerCapability(BaseModel):
    id: str  # references capability ID
    auth_options: List[HandlerAuthOption] = []


class HandlerTestConnection(BaseModel):
    type: str  # "endpoint" or "service"
    host: Optional[str] = None
    service: Optional[str] = None
    endpoint: str
    headers: Optional[Dict[str, str]] = None


class HandlerData(BaseModel):
    """Parsed structured data from a handler.yaml file."""

    id: str
    metadata: dict  # raw metadata dict
    enabled: bool = True
    triggering: HandlerTriggering
    capabilities: List[HandlerCapability] = []
    test_connection: HandlerTestConnection
    serializer: Optional[SerializerData] = None
    handler_dir_name: str  # directory name for path resolution
    resolved_params: List[ResolvedParamMapping] = []  # built by parser

    # Cross-link to matched Integration (set by ConnectorAwareInitializer)
    related_integration: Optional[Any] = None

    @property
    def module(self) -> Optional[str]:
        return self.metadata.get("module")

    @property
    def team(self) -> Optional[str]:
        return self.metadata.get("ownership", {}).get("team")

    @property
    def is_xsoar(self) -> bool:
        """Identify if this handler is XSOAR-related."""
        return self.module == "xsoar" or self.team == "xsoar"

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

    @property
    def xsoar_content_id(self) -> Optional[str]:
        if self.triggering.labels:
            return self.triggering.labels.get("xsoar-content-id")
        return None


# ============================================================
# Capability-handler mapping
# ============================================================


class CapabilityHandlerMapping(BaseModel):
    """Maps a capability to its handlers and related context."""

    capability_id: str
    handler_ids: List[str] = []
    is_xsoar: bool = False  # True if any handler for this capability is XSOAR
    auth_profile_ids: List[str] = []  # connection profile IDs used
    has_configurations: bool = False  # whether configurations.yaml has config for this


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
    connector_metadata: ConnectorMetadata = Field(alias="metadata")
    settings: Optional[ConnectorSettings] = None

    # === Parsed sub-models (populated by parser, excluded from serialization) ===
    connection: Optional[ConnectorConnectionData] = Field(None, exclude=True)
    capabilities: List[CapabilityData] = Field(default_factory=list, exclude=True)
    handlers: List[HandlerData] = Field(default_factory=list, exclude=True)
    capability_handler_map: Dict[str, CapabilityHandlerMapping] = Field(
        default_factory=dict, exclude=True
    )

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
        """Check if a dict/path represents a connector."""
        if path.name == "connector.yaml" or (path / "connector.yaml").exists():
            return True
        return "metadata" in _dict and "vendor" in _dict.get("metadata", {})

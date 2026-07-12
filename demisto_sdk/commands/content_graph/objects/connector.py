"""Connector content item - models a unified-connectors-content connector.

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

from pydantic import BaseModel, Field, root_validator

from demisto_sdk.commands.common.handlers import JSON_Handler
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
# Shared field sub-models
# ============================================================


class FieldModifiers(BaseModel):
    required: bool = False
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
# Connector identity - from connector.yaml
# ============================================================


class ConnectorOwnership(BaseModel):
    team: str
    maintainers: List[str] = []


class ConnectorMetadata(BaseModel):
    title: str
    description: str
    version: str  # semver e.g. "1.0.0"
    categories: List[str]  # classification categories, at least one required
    tags: List[str] = []
    domain: Optional[str] = None
    vendor: str
    publisher: str
    author_image: Optional[str] = None
    ownership: ConnectorOwnership


class ConnectorSettings(BaseModel):
    allow_skip_verification: bool = True


# ============================================================
# Connection data - parsed from connection.yaml
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
# Capability data - parsed from capabilities.yaml
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
# Serializer data - parsed from serializer.yaml
# (defined before HandlerData to avoid forward references)
# ============================================================


class FieldMapping(BaseModel):
    """Raw serializer entry from serializer.yaml."""

    id: str  # connector field ID (connector_param_name)
    field_name: (
        str  # value to transform integration parameter name (content_param_name) to
    )
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
# Handler data - parsed from components/handlers/<name>/handler.yaml
# ============================================================


class HandlerOwnership(BaseModel):
    """Ownership info from handler metadata."""

    team: str = ""
    maintainers: List[str] = []


class HandlerMetadata(BaseModel):
    """Typed metadata from a handler.yaml ``metadata`` block."""

    version: str = "1.0.0"
    description: str = ""
    module: Optional[str] = None
    tags: List[str] = []
    ownership: HandlerOwnership = HandlerOwnership()


class HandlerTriggering(BaseModel):
    type: str = "PUB_SUB"
    labels: Optional[Dict[str, str]] = None
    args: Optional[dict] = None


class HandlerAuthOption(BaseModel):
    id: str  # references connection profile ID
    scopes: Optional[List[str]] = []
    workloads: List[str] = []
    methods: Optional[List[str]] = []


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
    metadata: HandlerMetadata = HandlerMetadata()
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
        return self.metadata.module

    @property
    def team(self) -> str:
        return self.metadata.ownership.team

    @property
    def is_xsoar(self) -> bool:
        """Identify if this handler is XSOAR-related."""
        return self.module == "xsoar" and self.team == "xsoar"

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
            elif "allow_skip_verification" in values:
                values["settings"] = {
                    "allow_skip_verification": values["allow_skip_verification"]
                }

        return values

    # === Parsed sub-models (populated by parser, excluded from serialization) ===
    connection: Optional[ConnectorConnectionData] = Field(None, exclude=True)
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
            allow_skip = settings.get("allow_skip_verification")
            if isinstance(allow_skip, bool):
                json_dct["allow_skip_verification"] = allow_skip

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

"""Parser for unified-connectors-content Connector items.

Reads ``connector.yaml`` as the main file, discovers related files
(connection.yaml, capabilities.yaml, configurations.yaml, handler.yaml, etc.),
parses them into Pydantic sub-models, builds the capability-handler mapping,
and creates cross-repo relationships to content-repo Integrations and Packs.
"""

from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.content_graph.common import ContentType, RelationshipType
from demisto_sdk.commands.content_graph.objects.connector import (
    CapabilityData,
    CapabilityHandlerMapping,
    ComputedFieldRule,
    ConnectionProfile,
    ConnectorConnectionData,
    FieldGroup,
    FieldMapping,
    GeneralConfigurations,
    HandlerAuthOption,
    HandlerCapability,
    HandlerData,
    HandlerTestConnection,
    HandlerTriggering,
    ResolvedParamMapping,
    SerializerData,
    SubCapability,
)
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser
from demisto_sdk.commands.content_graph.parsers.related_files import (
    CapabilitiesRelatedFile,
    ConfigurationsRelatedFile,
    ConnectionRelatedFile,
    HandlerRelatedFile,
    SerializerRelatedFile,
    SummaryRelatedFile,
    TriggersRelatedFile,
)


class ConnectorParser(ContentItemParser, content_type=ContentType.CONNECTOR):
    """Parses a connector directory into a Connector content item.

    The connector directory structure is::

        connectors/<connector-name>/
            connector.yaml          # main file (required)
            connection.yaml         # auth profiles (required)
            capabilities.yaml       # capabilities (required)
            configurations.yaml     # per-capability config (optional)
            triggers.yaml           # triggers (optional)
            summary.yaml            # summary (optional)
            components/handlers/
                <handler-name>/
                    handler.yaml    # handler config (required per handler)
                    serializer.yaml # field mappings (optional)
    """

    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions] = list(MarketplaceVersions),
        pack_supported_modules: Optional[List[str]] = None,
        git_sha: Optional[str] = None,
    ) -> None:
        # Ensure path points to the connector directory
        if path.name == "connector.yaml":
            path = path.parent
        super().__init__(
            path,
            pack_marketplaces,
            pack_supported_modules=pack_supported_modules or [],
            git_sha=git_sha,
        )
        # Override structure_errors to be a proper list
        # (BaseContentParser sets it to a FieldInfo object)
        self.structure_errors = []

        # Parse connector.yaml fields
        self.connector_metadata: dict = self.yml_data.get("metadata", {})
        self.settings: Optional[dict] = self.yml_data.get("settings")

        # Create related files
        self._connection_rf = ConnectionRelatedFile(path, git_sha=git_sha)
        self._capabilities_rf = CapabilitiesRelatedFile(path, git_sha=git_sha)
        self._configurations_rf = ConfigurationsRelatedFile(path, git_sha=git_sha)
        self._triggers_rf = TriggersRelatedFile(path, git_sha=git_sha)
        self._summary_rf = SummaryRelatedFile(path, git_sha=git_sha)

        # Parse sub-models from related files
        self.connection: Optional[ConnectorConnectionData] = self._parse_connection()
        self.capabilities: List[CapabilityData] = (
            self._parse_capabilities_with_configs()
        )

        # Discover and parse handlers
        self.handlers: List[HandlerData] = self._parse_handlers()

        # Build capability-handler mapping
        self.capability_handler_map: Dict[str, CapabilityHandlerMapping] = (
            self._build_capability_handler_map()
        )

        # Create cross-repo relationships
        self._connect_to_content_items()

    @cached_property
    def yml_data(self) -> dict:
        return get_yaml(str(self.path / "connector.yaml"), git_sha=self.git_sha)

    @property
    def raw_data(self) -> dict:
        return self.yml_data

    @property
    def object_id(self) -> Optional[str]:
        return self.yml_data.get("id")

    @property
    def name(self) -> Optional[str]:
        return self.connector_metadata.get("title")

    @property
    def display_name(self) -> Optional[str]:
        return self.name

    @property
    def description(self) -> Optional[str]:
        return self.connector_metadata.get("description")

    @property
    def deprecated(self) -> bool:
        return False  # connectors don't have a deprecated flag currently

    @property
    def marketplaces(self) -> List[MarketplaceVersions]:
        return self.pack_marketplaces

    @property
    def is_silent(self) -> bool:
        return False

    @property
    def support(self) -> str:
        return ""

    @property
    def version(self) -> int:
        return 0

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return set(MarketplaceVersions)

    @property
    def fromversion(self) -> str:
        return DEFAULT_CONTENT_ITEM_FROM_VERSION

    @property
    def toversion(self) -> str:
        return DEFAULT_CONTENT_ITEM_TO_VERSION

    @property
    def strict_object(self):
        raise NotImplementedError("Connector does not have a strict object yet")

    def validate_structure(self):
        """Connectors don't have a strict object for structure validation yet."""
        return []

    # ============================================================
    # Sub-model parsing
    # ============================================================

    def _parse_connection(self) -> Optional[ConnectorConnectionData]:
        """Parse connection.yaml into ConnectorConnectionData."""
        data = self._connection_rf.file_content
        if not data:
            return None

        metadata = data.get("metadata", {})
        general_configs = self._parse_general_configurations(
            data.get("general_configurations")
        )
        profiles = [self._parse_connection_profile(p) for p in data.get("profiles", [])]

        return ConnectorConnectionData(
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            help=metadata.get("help"),
            general_configurations=general_configs,
            profiles=profiles,
        )

    def _parse_connection_profile(self, profile_data: dict) -> ConnectionProfile:
        """Parse a single connection profile."""
        configurations = [
            self._parse_field_group(fg) for fg in profile_data.get("configurations", [])
        ]
        return ConnectionProfile(
            id=profile_data["id"],
            type=profile_data["type"],
            title=profile_data.get("title", ""),
            description=profile_data.get("description"),
            discovery_url=profile_data.get("discovery_url"),
            token_endpoint=profile_data.get("token_endpoint"),
            authorization_endpoint=profile_data.get("authorization_endpoint"),
            client_id=profile_data.get("client_id"),
            client_secret=profile_data.get("client_secret"),
            refresh_token_scope=profile_data.get("refresh_token_scope"),
            options=profile_data.get("options"),
            configurations=configurations,
        )

    def _parse_capabilities_with_configs(self) -> List[CapabilityData]:
        """Parse capabilities.yaml and merge with configurations.yaml.

        Each capability gets a unified ``configurations`` list containing:
        1. general_configurations from capabilities.yaml (shared across all)
        2. general_configurations from configurations.yaml (shared across all)
        3. Per-capability configurations from configurations.yaml (matching by ID)
        """
        cap_data = self._capabilities_rf.file_content or {}
        cfg_data = self._configurations_rf.file_content or {}

        # Collect general configurations from both files
        general_field_groups: List[FieldGroup] = []

        # 1. general_configurations from capabilities.yaml
        cap_general = cap_data.get("general_configurations")
        if cap_general:
            for fg in cap_general.get("configurations", []):
                general_field_groups.append(self._parse_field_group(fg))

        # 2. general_configurations from configurations.yaml
        cfg_general = cfg_data.get("general_configurations")
        if cfg_general:
            for fg in cfg_general.get("configurations", []):
                general_field_groups.append(self._parse_field_group(fg))

        # Build per-capability config lookup from configurations.yaml
        per_cap_configs: Dict[str, List[FieldGroup]] = {}
        for cfg in cfg_data.get("configurations", []):
            cap_id = cfg.get("id", "")
            field_groups = [
                self._parse_field_group(fg) for fg in cfg.get("configurations", [])
            ]
            per_cap_configs[cap_id] = field_groups

        # Parse capabilities and merge configurations
        result: List[CapabilityData] = []
        for cap in cap_data.get("capabilities", []):
            config = cap.get("config")
            cap_config = None
            parent_license: List[str] = []
            if config:
                from demisto_sdk.commands.content_graph.objects.connector import (
                    CapabilityConfig,
                )

                parent_license = config.get("required_license", [])
                cap_config = CapabilityConfig(required_license=parent_license)

            sub_caps = [
                SubCapability(
                    id=sc["id"],
                    title=sc.get("title", ""),
                    default_enabled=sc.get("default_enabled", False),
                    required=sc.get("required", False),
                    # Use sub-capability's own required_license if present,
                    # otherwise inherit from the parent capability.
                    required_license=(
                        sc.get("config", {}).get("required_license") or parent_license
                    ),
                )
                for sc in cap.get("sub_capabilities", [])
            ]

            # Unified configurations: general + per-capability
            unified_configs = list(general_field_groups)  # copy
            if cap["id"] in per_cap_configs:
                unified_configs.extend(per_cap_configs[cap["id"]])

            result.append(
                CapabilityData(
                    id=cap["id"],
                    title=cap.get("title", ""),
                    description=cap.get("description", ""),
                    default_enabled=cap.get("default_enabled", False),
                    required=cap.get("required", False),
                    labels=cap.get("labels", []),
                    config=cap_config,
                    sub_capabilities=sub_caps,
                    configurations=unified_configs,
                )
            )
        return result

    def _parse_handlers(self) -> List[HandlerData]:
        """Discover and parse all handler directories."""
        handlers: List[HandlerData] = []
        handlers_dir = self.path / "components" / "handlers"
        if not handlers_dir.exists():
            return handlers

        for handler_dir in sorted(handlers_dir.iterdir()):
            if not handler_dir.is_dir():
                continue
            handler_rf = HandlerRelatedFile(
                self.path, handler_dir.name, git_sha=self.git_sha
            )
            if not handler_rf.exist or not handler_rf.file_content:
                continue

            hdata = handler_rf.file_content
            triggering_data = hdata.get("triggering", {})
            triggering = HandlerTriggering(
                type=triggering_data.get("type", ""),
                labels=triggering_data.get("labels"),
                args=triggering_data.get("args"),
            )

            handler_caps: List[HandlerCapability] = []
            for hcap in hdata.get("capabilities", []):
                auth_options = [
                    HandlerAuthOption(
                        id=ao["id"],
                        scopes=ao.get("scopes", []),
                        workloads=ao.get("workloads", []),
                        methods=ao.get("methods"),
                    )
                    for ao in hcap.get("auth_options", [])
                ]
                handler_caps.append(
                    HandlerCapability(id=hcap["id"], auth_options=auth_options)
                )

            tc_data = hdata.get("test_connection", {})
            test_connection = HandlerTestConnection(
                type=tc_data.get("type", ""),
                host=tc_data.get("host"),
                service=tc_data.get("service"),
                endpoint=tc_data.get("endpoint", ""),
                headers=tc_data.get("headers"),
            )

            # Parse serializer if exists
            serializer: Optional[SerializerData] = None
            ser_rf = SerializerRelatedFile(
                self.path, handler_dir.name, git_sha=self.git_sha
            )
            if ser_rf.exist and ser_rf.file_content:
                ser_data = ser_rf.file_content
                field_mappings = [
                    FieldMapping(
                        id=fm["id"],
                        field_name=fm["field_name"],
                        field_value=fm.get("field_value"),
                    )
                    for fm in ser_data.get("field_mappings", [])
                ]
                computed_fields = [
                    ComputedFieldRule(
                        output=cf.get("output", []),
                        any_of=cf.get("any_of", []),
                    )
                    for cf in ser_data.get("computed_fields", [])
                ]
                serializer = SerializerData(
                    field_mappings=field_mappings,
                    computed_fields=computed_fields,
                )

            handler_data = HandlerData(
                id=hdata["id"],
                metadata=hdata.get("metadata", {}),
                enabled=hdata.get("enabled", True),
                triggering=triggering,
                capabilities=handler_caps,
                test_connection=test_connection,
                serializer=serializer,
                handler_dir_name=handler_dir.name,
            )

            # Build resolved parameter mappings
            handler_data.resolved_params = self._build_resolved_params(handler_data)
            handlers.append(handler_data)

        return handlers

    # ============================================================
    # Resolved parameter mapping
    # ============================================================

    def _build_resolved_params(
        self, handler: HandlerData
    ) -> List[ResolvedParamMapping]:
        """Build the connector_param_name <-> content_param_name mapping for a handler.

        For each connector field visible to this handler:
        - If the field ID appears in the serializer, use the serializer's field_name
          as content_param_name
        - If not, both connector_param_name and content_param_name equal the field ID
        """
        # Build serializer lookup: connector field ID -> FieldMapping
        serializer_map: Dict[str, FieldMapping] = {}
        if handler.serializer:
            for fm in handler.serializer.field_mappings:
                serializer_map[fm.id] = fm

        resolved: List[ResolvedParamMapping] = []
        all_fields = self._collect_handler_fields(handler)

        seen: Set[str] = set()
        for field_id, source_file in all_fields:
            if field_id in seen:
                continue
            seen.add(field_id)

            if field_id in serializer_map:
                fm = serializer_map[field_id]
                resolved.append(
                    ResolvedParamMapping(
                        connector_param_name=field_id,
                        content_param_name=fm.field_name,
                        field_value_transform=fm.field_value,
                        is_serialized=True,
                        source_file=source_file,
                    )
                )
            else:
                resolved.append(
                    ResolvedParamMapping(
                        connector_param_name=field_id,
                        content_param_name=field_id,
                        is_serialized=False,
                        source_file=source_file,
                    )
                )

        return resolved

    def _collect_handler_fields(self, handler: HandlerData) -> List[Tuple[str, str]]:
        """Collect all connector field IDs relevant to a handler.

        Returns list of (field_id, source_file) tuples.
        Fields come from:
        1. connection.yaml general_configurations (shared across all handlers)
        2. connection.yaml profiles used by this handler's auth_options
        3. capabilities.yaml general_configurations
        4. configurations.yaml entries matching this handler's capability IDs
        """
        fields: List[Tuple[str, str]] = []

        # 1. Connection general configurations
        if self.connection and self.connection.general_configurations:
            for group in self.connection.general_configurations.configurations:
                for f in group.fields:
                    fields.append((f.id, "connection.yaml"))

        # 2. Connection profiles used by this handler
        handler_auth_ids: Set[str] = {
            ao.id for hc in handler.capabilities for ao in hc.auth_options
        }
        if self.connection:
            for profile in self.connection.profiles:
                if profile.id in handler_auth_ids:
                    for group in profile.configurations:
                        for f in group.fields:
                            fields.append((f.id, "connection.yaml"))

        # 3. Capabilities general configurations
        cap_data = self._capabilities_rf.file_content
        if cap_data:
            gen_cfg = cap_data.get("general_configurations")
            if gen_cfg:
                for fg in gen_cfg.get("configurations", []):
                    for f in fg.get("fields", []):
                        fields.append((f.get("id", ""), "capabilities.yaml"))

        # 4. Configurations for this handler's capabilities (already unified in CapabilityData)
        handler_cap_ids: Set[str] = {hc.id for hc in handler.capabilities}
        for cap in self.capabilities:
            if cap.id in handler_cap_ids:
                for group in cap.configurations:
                    for f in group.fields:
                        fields.append((f.id, "configurations.yaml"))

        return fields

    # ============================================================
    # Capability-handler mapping
    # ============================================================

    def _build_capability_handler_map(
        self,
    ) -> Dict[str, CapabilityHandlerMapping]:
        """Cross-reference capabilities, handlers, and configurations."""
        mapping: Dict[str, CapabilityHandlerMapping] = {}

        # Register all capabilities (including sub-capabilities)
        for cap in self.capabilities:
            mapping[cap.id] = CapabilityHandlerMapping(capability_id=cap.id)
            for sub in cap.sub_capabilities:
                mapping[sub.id] = CapabilityHandlerMapping(capability_id=sub.id)

        # Map handlers to capabilities
        for handler in self.handlers:
            for handler_cap in handler.capabilities:
                if handler_cap.id in mapping:
                    mapping[handler_cap.id].handler_ids.append(handler.id)
                    if handler.is_xsoar:
                        mapping[handler_cap.id].is_xsoar = True
                    for auth_opt in handler_cap.auth_options:
                        if auth_opt.id not in mapping[handler_cap.id].auth_profile_ids:
                            mapping[handler_cap.id].auth_profile_ids.append(auth_opt.id)

        # Check which capabilities have configurations
        for cap in self.capabilities:
            if cap.id in mapping and cap.configurations:
                mapping[cap.id].has_configurations = True

        return mapping

    # ============================================================
    # Cross-repo relationships
    # ============================================================

    def _connect_to_content_items(self) -> None:
        """Create relationships to content repo items via handler labels."""
        for handler in self.handlers:
            if integration_id := handler.xsoar_integration_id:
                self.add_relationship(
                    RelationshipType.REFERENCES_INTEGRATION,
                    target=integration_id,
                    target_type=ContentType.INTEGRATION,
                )
            if pack_id := handler.xsoar_pack_id:
                self.add_relationship(
                    RelationshipType.REFERENCES_PACK,
                    target=pack_id,
                    target_type=ContentType.PACK,
                )

    # ============================================================
    # Helpers
    # ============================================================

    @staticmethod
    def _parse_general_configurations(
        data: Optional[dict],
    ) -> Optional[GeneralConfigurations]:
        """Parse a general_configurations block."""
        if not data:
            return None
        from demisto_sdk.commands.content_graph.objects.connector import ConnectorField

        field_groups: List[FieldGroup] = []
        for fg in data.get("configurations", []):
            fields = [
                ConnectorField(
                    id=f["id"],
                    title=f.get("title", ""),
                    field_type=f.get("field_type", "input"),
                    metadata=f.get("metadata"),
                    validations=f.get("validations"),
                    behavior=f.get("behavior"),
                )
                for f in fg.get("fields", [])
            ]
            field_groups.append(FieldGroup(fields=fields))

        return GeneralConfigurations(
            description=data.get("description"),
            configurations=field_groups,
        )

    @staticmethod
    def _parse_field_group(fg_data: dict) -> FieldGroup:
        """Parse a single field group."""
        from demisto_sdk.commands.content_graph.objects.connector import ConnectorField

        fields = [
            ConnectorField(
                id=f["id"],
                title=f.get("title", ""),
                field_type=f.get("field_type", "input"),
                metadata=f.get("metadata"),
                validations=f.get("validations"),
                behavior=f.get("behavior"),
            )
            for f in fg_data.get("fields", [])
        ]
        return FieldGroup(fields=fields)

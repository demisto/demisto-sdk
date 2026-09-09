import enum
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Set

from neo4j import graph
from pydantic import BaseModel
from ruamel.yaml.scalarstring import (  # noqa: TID251 - only importing FoldedScalarString is OK
    FoldedScalarString,
)

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_NEO4J_DATABASE_HTTP,
    DEMISTO_SDK_NEO4J_DATABASE_URL,
    DEMISTO_SDK_NEO4J_PASSWORD,
    DEMISTO_SDK_NEO4J_USERNAME,
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
    PACK_NAME_DEPRECATED_REGEX,
    PACKS_FOLDER,
    XSOAR_SUPPORT,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.git_content_config import GitContentConfig
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.StrEnum import StrEnum
from demisto_sdk.commands.common.tools import (
    get_dict_from_file,
    get_json,
    get_remote_file,
    pascalToSpace,
)

NEO4J_ADMIN_DOCKER = ""

NEO4J_DATABASE_HTTP = os.getenv(
    DEMISTO_SDK_NEO4J_DATABASE_HTTP, "http://127.0.0.1:7474"
)
NEO4J_DATABASE_URL = os.getenv(DEMISTO_SDK_NEO4J_DATABASE_URL, "neo4j://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv(DEMISTO_SDK_NEO4J_USERNAME, "neo4j")
NEO4J_PASSWORD = os.getenv(DEMISTO_SDK_NEO4J_PASSWORD, "contentgraph")

PACK_METADATA_FILENAME = "pack_metadata.json"
VERSION_CONFIG_FILENAME = "version_config.json"
PACK_CONTRIBUTORS_FILENAME = "CONTRIBUTORS.json"
UNIFIED_FILES_SUFFIXES = [".yml", ".json"]

SERVER_CONTENT_ITEMS_PATH = Path("Tests/Marketplace/server_content_items.json")


class Neo4jRelationshipResult(NamedTuple):
    node_from: graph.Node
    relationships: List[graph.Relationship]
    nodes_to: List[graph.Node]


class RelationshipType(StrEnum):
    DEPENDS_ON = "DEPENDS_ON"
    HAS_COMMAND = "HAS_COMMAND"
    IMPORTS = "IMPORTS"
    IN_PACK = "IN_PACK"
    REFERENCES_INTEGRATION = "REFERENCES_INTEGRATION"
    REFERENCES_PACK = "REFERENCES_PACK"
    TESTED_BY = "TESTED_BY"
    USES = "USES"
    USES_BY_ID = "USES_BY_ID"
    USES_BY_NAME = "USES_BY_NAME"
    USES_BY_CLI_NAME = "USES_BY_CLI_NAME"
    USES_COMMAND_OR_SCRIPT = "USES_COMMAND_OR_SCRIPT"
    USES_PLAYBOOK = "USES_PLAYBOOK"


class ContentType(StrEnum):
    BASE_CONTENT = "BaseContent"
    BASE_NODE = "BaseNode"
    BASE_PLAYBOOK = "BasePlaybook"
    CLASSIFIER = "Classifier"
    COMMAND = "Command"
    COMMAND_OR_SCRIPT = "CommandOrScript"
    CORRELATION_RULE = "CorrelationRule"
    DASHBOARD = "Dashboard"
    GENERIC_DEFINITION = "GenericDefinition"
    GENERIC_FIELD = "GenericField"
    GENERIC_MODULE = "GenericModule"
    GENERIC_TYPE = "GenericType"
    INCIDENT_FIELD = "IncidentField"
    INCIDENT_TYPE = "IncidentType"
    INDICATOR_FIELD = "IndicatorField"
    INDICATOR_TYPE = "IndicatorType"
    INTEGRATION = "Integration"
    JOB = "Job"
    LAYOUT = "Layout"
    LIST = "List"
    MAPPER = "Mapper"
    MODELING_RULE = "ModelingRule"
    PACK = "Pack"
    PARSING_RULE = "ParsingRule"
    PLAYBOOK = "Playbook"
    PREPROCESS_RULE = "PreProcessRule"
    REPORT = "Report"
    BASE_SCRIPT = "BaseScript"
    SCRIPT = "Script"
    TEST_SCRIPT = "TestScript"
    TEST_PLAYBOOK = "TestPlaybook"
    TRIGGER = "Trigger"
    WIDGET = "Widget"
    XSIAM_DASHBOARD = "XSIAMDashboard"
    XSIAM_REPORT = "XSIAMReport"
    WIZARD = "Wizard"
    XDRC_TEMPLATE = "XDRCTemplate"
    LAYOUT_RULE = "LayoutRule"
    ASSETS_MODELING_RULE = "AssetsModelingRule"
    CASE_LAYOUT_RULE = "CaseLayoutRule"
    CASE_FIELD = "CaseField"
    CASE_LAYOUT = "CaseLayout"
    AGENTIX_AGENT = "AgentixAgent"
    AGENTIX_ACTION = "AgentixAction"
    AGENTIX_ACTION_TEST = "AgentixActionTest"
    AGENTIX_SKILL = "AgentixSkill"
    COLLECTION = "Collection"
    CONNECTOR = "Connector"

    @property
    def labels(self) -> List[str]:
        labels: Set[str] = {ContentType.BASE_NODE.value, self.value}
        if self.value != ContentType.COMMAND:
            labels.add(ContentType.BASE_CONTENT.value)
        if self.value in [ContentType.TEST_PLAYBOOK.value, ContentType.PLAYBOOK.value]:
            labels.add(ContentType.BASE_PLAYBOOK.value)
        if self.value in [ContentType.SCRIPT.value, ContentType.TEST_SCRIPT.value]:
            labels.add(ContentType.BASE_SCRIPT.value)

        if self in [
            ContentType.SCRIPT,
            ContentType.COMMAND,
            ContentType.BASE_SCRIPT,
            ContentType.TEST_SCRIPT,
        ]:
            labels.add(ContentType.COMMAND_OR_SCRIPT.value)

        return list(labels)

    @property
    def server_name(self) -> str:
        if self == ContentType.INDICATOR_TYPE:
            return "reputation"
        elif self == ContentType.INDICATOR_FIELD:
            return "incidentfield-indicatorfield"
        elif self == ContentType.CASE_FIELD:
            return "casefield"
        elif self in (ContentType.LAYOUT, ContentType.CASE_LAYOUT):
            return "layoutscontainer"
        elif self == ContentType.PREPROCESS_RULE:
            return "preprocessrule"
        elif self == ContentType.TEST_PLAYBOOK:
            return ContentType.PLAYBOOK.server_name
        elif self == ContentType.MAPPER:
            return "classifier-mapper"
        elif self == ContentType.COLLECTION:
            return "agentixknowledgecollection"
        return self.lower()

    # def __hash__(self) -> int:
    #     return hash(self.value)

    @property
    def metadata_name(self) -> str:
        if self == ContentType.SCRIPT:
            return "automation"
        elif self == ContentType.INDICATOR_TYPE:
            return "reputation"
        elif self in (ContentType.LAYOUT, ContentType.CASE_LAYOUT):
            return "layoutscontainer"
        elif self == ContentType.TEST_PLAYBOOK:
            return ContentType.PLAYBOOK.server_name
        elif self == ContentType.MAPPER:
            return "classifier"
        elif self == ContentType.COLLECTION:
            return "agentixknowledgecollection"
        return self.lower()

    @property
    def metadata_display_name(self) -> str:
        if self == ContentType.SCRIPT:
            return "Automation"
        elif self == ContentType.INDICATOR_TYPE:
            return "Reputation"
        elif self == ContentType.MAPPER:
            return "Classifier"
        elif self in (ContentType.LAYOUT, ContentType.CASE_LAYOUT):
            return "Layouts Container"
        else:
            return re.sub(r"([a-z](?=[A-Z])|[A-Z](?=[A-Z][a-z]))", r"\1 ", self.value)

    @staticmethod
    def server_names() -> List[str]:
        return [c.server_name for c in ContentType] + ["indicatorfield", "mapper"]

    @staticmethod
    def values() -> Iterator[str]:
        return (c.value for c in ContentType)

    @staticmethod
    def _is_agentix_action_test_path(path: Path) -> bool:
        """
        Check if the given path represents an AgentixActionTest file.

        Detects two patterns:
        - New pattern: *_test.yml (e.g., EnrichIP_test.yml)
        - Old pattern: test_*.yaml in test_data directory

        Note: This method intentionally does NOT check directories.
        A directory under AgentixActions/ may contain both an action file
        and a test file, so the directory itself should not be classified
        as a test path.

        Args:
            path: The path to check

        Returns:
            True if the path represents an AgentixActionTest file, False otherwise
        """
        # Check for test file patterns
        if path.stem.endswith("_test") or (
            path.stem.startswith("test_") and "test_data" in path.parts
        ):
            return True

        return False

    @staticmethod
    def _is_agentix_agent_test_path(path: Path) -> bool:
        """
        Check if the given path represents a test file under AgentixAgents.

        Test files (e.g., CloudPostureAgent_test.yml) live alongside agent
        files in the same directory and should NOT be parsed as content items.

        Note: This method intentionally does NOT use path.is_file() or check
        directories, as the path may not exist on the filesystem (e.g., when
        coming from git).

        Args:
            path: The path to check

        Returns:
            True if the path represents a test file under AgentixAgents, False otherwise
        """
        if path.suffix in (".yml", ".yaml") and path.stem.endswith("_test"):
            return True
        return False

    @classmethod
    def by_path(cls, path: Path) -> "ContentType":
        for idx, folder in enumerate(path.parts):
            if folder == PACKS_FOLDER:
                if len(path.parts) <= idx + 2:
                    raise ValueError("Invalid content path.")
                content_type_dir = path.parts[idx + 2]

                # Special handling for AgentixActionTest files
                if content_type_dir == "AgentixActions":
                    if cls._is_agentix_action_test_path(path):
                        return cls.AGENTIX_ACTION_TEST

                # Skip test files under AgentixAgents - they are not content items
                if content_type_dir == "AgentixAgents":
                    if cls._is_agentix_agent_test_path(path):
                        raise ValueError(
                            f"Test file under AgentixAgents is not a content item: {path}"
                        )

                break
        else:
            # less safe option - will raise an exception if the path
            # is not to the content item directory or file
            if path.parts[-2][:-1] in ContentType.values():
                content_type_dir = path.parts[-2]
            elif path.parts[-3][:-1] in ContentType.values():
                content_type_dir = path.parts[-3]
            else:
                raise ValueError(f"Could not find content type in path {path}")
        return cls(content_type_dir[:-1])  # remove the `s`

    @staticmethod
    def folders() -> List[str]:
        return [c.as_folder for c in ContentType]

    @property
    def as_folder(self) -> str:
        if self == ContentType.MAPPER:
            return f"{ContentType.CLASSIFIER}s"
        return f"{self.value}s"

    @staticmethod
    def abstract_types() -> List["ContentType"]:
        return [
            ContentType.BASE_NODE,
            ContentType.BASE_CONTENT,
            ContentType.COMMAND_OR_SCRIPT,
        ]

    @staticmethod
    def non_content_items() -> List["ContentType"]:
        return [ContentType.PACK, ContentType.COMMAND]

    @staticmethod
    def non_abstracts(
        include_non_content_items: bool = True,
    ) -> Iterator["ContentType"]:
        for content_type in ContentType:
            if content_type in ContentType.abstract_types():
                continue
            if (
                not include_non_content_items
                and content_type in ContentType.non_content_items()
            ):
                continue
            yield content_type

    @staticmethod
    def content_items() -> Iterator["ContentType"]:
        return ContentType.non_abstracts(include_non_content_items=False)

    @property
    def is_tightly_coupled(self) -> bool:
        """Whether this content type travels with the pack to Managed Content."""
        return self in TIGHTLY_COUPLED_TYPES

    @classmethod
    def tightly_coupled_types(cls) -> "frozenset[ContentType]":
        """Return the frozenset of tightly coupled content types."""
        return TIGHTLY_COUPLED_TYPES

    @classmethod
    def loosely_coupled_types(cls) -> "frozenset[ContentType]":
        """Return content item types that are loosely coupled — Marketplace only."""
        return frozenset(cls.content_items()) - TIGHTLY_COUPLED_TYPES

    @staticmethod
    def threat_intel_report_types() -> List["ContentType"]:
        return [ContentType.GENERIC_FIELD, ContentType.GENERIC_TYPE]

    @staticmethod
    def pack_folders(pack_path: Path) -> Iterator[Path]:
        for content_type in ContentType.content_items():
            if content_type == ContentType.MAPPER:
                continue
            pack_folder = pack_path / content_type.as_folder
            if pack_folder.is_dir() and not pack_folder.name.startswith("."):
                if content_type not in ContentType.threat_intel_report_types():
                    yield pack_folder
                else:
                    for tir_folder in pack_folder.iterdir():
                        if tir_folder.is_dir() and not tir_folder.name.startswith("."):
                            yield tir_folder

    @staticmethod
    def by_schema(path: Path, git_sha: Optional[str] = None) -> "ContentType":
        """
        Determines a content type value of a given file by accessing it and making minimal checks on its schema.
        """
        from demisto_sdk.commands.content_graph.objects.base_content import (
            CONTENT_TYPE_TO_MODEL,
        )

        parsed_dict = get_dict_from_file(str(path), git_sha=git_sha)
        if parsed_dict and isinstance(parsed_dict, tuple):
            _dict = parsed_dict[0]
        else:
            _dict = parsed_dict
        for content_type in ContentType.content_items():
            if content_type_obj := CONTENT_TYPE_TO_MODEL.get(content_type):
                if content_type_obj.match(_dict, path):
                    return content_type
        raise ValueError(f"Could not find content type in path {path}")

    @property
    def as_rn_header(self) -> str:
        """
        Convert ContentType to the Release note header.
        """
        if self == ContentType.PREPROCESS_RULE:
            return "PreProcess Rules"
        elif self == ContentType.TRIGGER:
            return "Triggers Recommendations"  # https://github.com/demisto/etc/issues/48153#issuecomment-1111988526
        elif self == ContentType.XSIAM_REPORT:
            return "XSIAM Reports"
        elif self == ContentType.XDRC_TEMPLATE:
            return "XDRC Templates"
        elif self == ContentType.XSIAM_DASHBOARD:
            return "XSIAM Dashboards"
        elif self == ContentType.GENERIC_TYPE:
            return "Object Types"
        elif self == ContentType.GENERIC_FIELD:
            return "Object Fields"
        elif self == ContentType.GENERIC_DEFINITION:
            return "Objects"
        elif self == ContentType.GENERIC_MODULE:
            return "Modules"
        elif self == ContentType.CASE_LAYOUT:
            return "Layouts"
        elif self == ContentType.AGENTIX_AGENT:
            return "Agents"
        elif self == ContentType.AGENTIX_ACTION:
            return "Actions"
        elif self == ContentType.AGENTIX_SKILL:
            return "Skills"
        elif self == ContentType.COLLECTION:
            return "Collections"
        separated_str = pascalToSpace(self)
        return f"{separated_str}s"

    @staticmethod
    def convert_header_to_content_type(header: str) -> "ContentType":
        """
        Convert Release note header to ContentType.
        """
        if header == "Triggers Recommendations":
            return ContentType.TRIGGER
        elif header == "Preprocess Rules":
            return ContentType.PREPROCESS_RULE
        elif header == "Mappers":
            return ContentType.MAPPER
        elif header == "Objects":
            return ContentType.GENERIC_DEFINITION
        elif header == "Modules":
            return ContentType.GENERIC_MODULE
        elif header == "Object Types":
            return ContentType.GENERIC_TYPE
        elif header == "Object Fields":
            return ContentType.GENERIC_FIELD
        elif header == "Agents":
            return ContentType.AGENTIX_AGENT
        elif header == "Actions":
            return ContentType.AGENTIX_ACTION
        elif header == "Skills":
            return ContentType.AGENTIX_SKILL
        elif header == "Collections":
            return ContentType.COLLECTION
        normalized_header = header.rstrip("s").replace(" ", "_").upper()
        return ContentType[normalized_header]


# ---------------------------------------------------------------------------
# Coupling classification — which content types travel with the pack to
# Managed Content vs. staying in Marketplace only.
# ---------------------------------------------------------------------------

TIGHTLY_COUPLED_TYPES: frozenset[ContentType] = frozenset(
    {
        ContentType.INTEGRATION,
        ContentType.MODELING_RULE,
        ContentType.PARSING_RULE,
        ContentType.ASSETS_MODELING_RULE,
        ContentType.MAPPER,
        ContentType.CLASSIFIER,
        ContentType.INCIDENT_FIELD,
        ContentType.INCIDENT_TYPE,
        ContentType.INDICATOR_FIELD,
        ContentType.INDICATOR_TYPE,
        ContentType.CASE_FIELD,
    }
)

# The raw yml/json key an item author sets to opt a single content item out of
# tight coupling, even though its ContentType is in ``TIGHTLY_COUPLED_TYPES``.
# Spelled identically in both YAML and JSON content items, like the other
# generic item-level flags (``marketplaces``, ``deprecated``, ``issilent``).
EXCLUDE_FROM_TIGHTLY_COUPLED_KEY: str = "excludefromtightlycoupled"


class PackDestination(str, enum.Enum):
    """Describes where a pack's content is destined during the build process."""

    MARKETPLACE = "marketplace"
    MANAGED_CONTENT = "managed_content"


DERIVED_PACK_SUFFIX = "Managed"

# Feature flag: when False, derived pack generation is skipped entirely.
ENABLE_SPLIT_PACKS = os.getenv("ENABLE_SPLIT_PACKS", "false").lower() == "true"

# The feature name every derived (split) pack is published under, unless
# overridden. Consumed downstream as the pack's ``source``, which determines the
# Managed Content bucket layout: <bucket>/<bucket_path>/<source>/<pack_id>/.
DEFAULT_DERIVED_PACK_SOURCE = "connectus"


def resolve_derived_pack_source(pack_derived_source: Optional[str] = None) -> str:
    """Resolve the ``source`` (feature name) assigned to a derived pack.

    Precedence, highest first:
        1. ``pack_derived_source`` - the ``derived_source`` field of the
           originating pack's ``pack_metadata.json``. Scopes to a single pack.
        2. ``DERIVED_PACK_SOURCE`` environment variable. Redirects every derived
           pack in the run at once, which is what CI sets.
        3. ``DEFAULT_DERIVED_PACK_SOURCE``.

    The environment is read here rather than at module import (unlike
    ``ENABLE_SPLIT_PACKS``) so the value stays overridable in tests and is not
    sensitive to import order.

    Args:
        pack_derived_source: Per-pack override from pack metadata, if declared.

    Returns:
        The feature name to publish the derived pack under.
    """
    if pack_derived_source:
        return pack_derived_source
    return os.getenv("DERIVED_PACK_SOURCE") or DEFAULT_DERIVED_PACK_SOURCE


# Environment variable holding a comma-separated list of pack ids (folder names)
# that must never yield a derived (split) pack, regardless of their content.
DERIVED_PACKS_EXCLUDE_ENV = "DERIVED_PACKS_EXCLUDE"

# Only xsoar-supported packs may be split. Partner/community/developer packs -
# and packs declaring no support at all - are never eligible.
DERIVED_PACK_ALLOWED_SUPPORT_LEVELS: frozenset[str] = frozenset({XSOAR_SUPPORT})

DERIVED_PACKS_EXCLUDE_SEPARATOR = ","


def derived_pack_exclusions() -> frozenset[str]:
    """The set of pack ids explicitly excluded from derived (split) pack generation.

    The value is read from the ``DERIVED_PACKS_EXCLUDE`` environment variable, a
    comma-separated list of pack ids (the pack folder name, i.e.
    ``pack.object_id``). Entries are stripped and casefolded, so matching is
    case-insensitive and insensitive to whitespace around the separators. Blank
    entries are dropped.

    The environment is read per call (like ``resolve_derived_pack_source`` and
    unlike ``ENABLE_SPLIT_PACKS``) so the value stays overridable in tests and is
    not sensitive to import order.

    Returns:
        The casefolded pack ids to exclude; empty when the variable is unset or blank.
    """
    raw = os.getenv(DERIVED_PACKS_EXCLUDE_ENV) or ""
    return frozenset(
        entry.strip().casefold()
        for entry in raw.split(DERIVED_PACKS_EXCLUDE_SEPARATOR)
        if entry.strip()
    )


# ---------------------------------------------------------------------------
# Deprecation - one canonical rule, applied identically to packs and to
# content items by the split-pack (derived pack) logic.
#
# NOTE: this helper is deliberately scoped to the split-pack logic. The legacy
# per-entity ``deprecated`` properties (``PackParser.deprecated``,
# ``YAMLContentItemParser.deprecated``, ``JSONContentItemParser.deprecated``)
# are left exactly as they are, so unrelated consumers keep their current
# behaviour. Everything deciding derived-pack eligibility or tight coupling goes
# through the functions below instead.
# ---------------------------------------------------------------------------

# The explicit deprecation field, spelled identically in ``pack_metadata.json``
# and in a content item's yml/json.
DEPRECATED_FIELD = "deprecated"


def is_deprecated_entity(
    name: Optional[str],
    description: Optional[str],
    deprecated_field: Optional[bool] = None,
) -> bool:
    """The canonical deprecation predicate, shared by packs and content items.

    An entity is deprecated when EITHER holds:
        1. its explicit ``deprecated`` field is truthy (``deprecated`` in a
           content item's yml/json, ``deprecated`` in ``pack_metadata.json``), or
        2. its display name is marked ``(Deprecated)`` AND its description
           follows one of the deprecation description conventions
           (``Deprecated. Use X instead.`` / ``Deprecated. No available replacement.``).

    Rule 2 is the historical pack-level heuristic; applying it to content items as
    well is what makes this predicate uniform across both entity kinds.

    Args:
        name: The entity display name, if any.
        description: The entity description, if any.
        deprecated_field: The value of the entity's explicit ``deprecated`` field, if any.

    Returns:
        True if the entity is deprecated under either rule.
    """
    if deprecated_field:
        return True
    if not isinstance(name, str) or not isinstance(description, str):
        return False
    return bool(
        re.match(PACK_NAME_DEPRECATED_REGEX, name)
        and (
            re.match(DEPRECATED_NO_REPLACE_DESC_REGEX, description)
            or re.match(DEPRECATED_DESC_REGEX, description)
        )
    )


def is_deprecated_content_item(content_item: Any) -> bool:
    """Apply ``is_deprecated_entity`` to a content item.

    Works for both the parser representation
    (``content_graph.parsers.content_item.ContentItemParser``) and the object
    representation (``content_graph.objects.content_item.ContentItem``), which
    expose the same ``name`` / ``description`` / ``deprecated`` surface.

    Args:
        content_item: The content item (parser or object) to inspect.

    Returns:
        True if the content item is deprecated.
    """
    return is_deprecated_entity(
        name=getattr(content_item, "name", None),
        description=getattr(content_item, "description", None),
        deprecated_field=getattr(content_item, DEPRECATED_FIELD, None),
    )


def is_deprecated_pack(pack: Any) -> bool:
    """Apply ``is_deprecated_entity`` to a pack.

    Works for both the parser representation
    (``content_graph.parsers.pack.PackParser``) and the object representation
    (``content_graph.objects.pack.Pack``).

    Unlike the legacy ``PackParser.deprecated`` property - which is left
    untouched and consults the name/description convention only - this also
    honours an explicit ``deprecated`` field in ``pack_metadata.json``.

    Args:
        pack: The pack (parser or object) to inspect.

    Returns:
        True if the pack is deprecated.
    """
    metadata = getattr(pack, "pack_metadata_dict", None) or {}
    return is_deprecated_entity(
        name=getattr(pack, "name", None),
        description=getattr(pack, "description", None),
        deprecated_field=metadata.get(DEPRECATED_FIELD)
        or getattr(pack, DEPRECATED_FIELD, None),
    )


class Relationship(BaseModel):
    relationship: Optional[RelationshipType] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    source_type: Optional[ContentType] = None
    source_fromversion: Optional[str] = None
    source_marketplaces: Optional[List[MarketplaceVersions]]
    target: Optional[str] = None
    target_type: Optional[ContentType] = None
    target_min_version: Optional[str] = None
    mandatorily: Optional[bool] = None
    description: Optional[str] = None
    deprecated: Optional[bool] = None
    name: Optional[str] = None
    quickaction: Optional[bool] = None
    compliantpolicies: Optional[list[str]] = None
    supportedModules: Optional[list[str]] = None


class Relationships(dict):
    def add(self, relationship: RelationshipType, **kwargs):
        if relationship not in self.keys():
            self.__setitem__(relationship, [])
        self.__getitem__(relationship).append(
            Relationship.parse_obj(kwargs).dict(exclude_none=True)
        )

    def add_batch(self, relationship: RelationshipType, data: List[Dict[str, Any]]):
        if relationship not in self.keys():
            self.__setitem__(relationship, [])
        data = [Relationship.parse_obj(item).dict(exclude_none=True) for item in data]
        self.__getitem__(relationship).extend(data)

    def update(self, other: "Relationships") -> None:  # type: ignore
        for relationship, parsed_data in other.items():
            if relationship not in RelationshipType or not isinstance(
                parsed_data, list
            ):
                raise TypeError
            self.add_batch(relationship, parsed_data)


class Nodes(dict):
    def __init__(self, *args) -> None:
        super().__init__(self)
        for arg in args:
            if not isinstance(arg, dict):
                raise ValueError(f"Expected a dict: {arg}")
        self.add_batch(args)  # type: ignore[arg-type]

    def add(self, **kwargs):
        content_type: ContentType = ContentType(kwargs["content_type"])
        if content_type not in self.keys():
            self.__setitem__(content_type, [])
        self.__getitem__(content_type).append(kwargs)

    def add_batch(self, data: Iterator[Dict[str, Any]]):
        for obj in data:
            self.add(**obj)

    def update(self, other: "Nodes") -> None:  # type: ignore[override]
        data: Iterator[Dict[str, Any]]
        for content_type, data in other.items():
            if content_type not in ContentType or not isinstance(data, list):
                raise TypeError
            self.add_batch(data)


class PackTags:
    """Pack tag constants"""

    TRENDING = "Trending"
    NEW = "New"
    TIM = "TIM"
    USE_CASE = "Use Case"
    TRANSFORMER = "Transformer"
    FILTER = "Filter"
    COLLECTION = "Collection"
    DATA_SOURCE = "Data Source"
    MCP = "MCP"


class LazyProperty(property):
    """
    Used to define the properties which are lazy properties
    """

    pass


def lazy_property(property_func: Callable):
    """
    lazy property: specifies that this property should be added to the pydantic model lazily
    only when the instance property is first accessed.

    Note:
        make sure that the lazy property returns only primitive objects (bool, str, int, float, list).

    Use this decorator on your property in case you need it to be added to the model only if its called directly
    """

    def _lazy_decorator(self):
        property_name = property_func.__name__

        if property_output := self.__dict__.get(property_name):
            return property_output

        property_output = property_func(self)

        self.__dict__[property_name] = property_output
        return property_output

    return LazyProperty(_lazy_decorator)


def get_server_content_items(tag: Optional[str] = None) -> Dict[ContentType, list]:
    """Reads a JSON file containing server content items from content repository
    and returns a dict representation of it in the required format.
    Args:
        tag (Optional[str], optional): A tag to get the server content items from.
            If not specified, the server content items will be read from the local file.
    Returns:
        Dict[ContentType, list]: A mapping of content types to the list of server content items.
    """
    from_remote = tag is not None or not SERVER_CONTENT_ITEMS_PATH.exists()
    if not from_remote:
        json_data: dict = get_json(str(SERVER_CONTENT_ITEMS_PATH))
    else:
        json_data = get_remote_file(
            str(SERVER_CONTENT_ITEMS_PATH),
            git_content_config=GitContentConfig(
                repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME,
            ),
            tag=tag,
        )
    return {ContentType(k): v for k, v in json_data.items()}


# Used to remove content-private nodes, as a temporary temporary workaround.
# For more details: https://jira-hq.paloaltonetworks.local/browse/CIAC-7149
CONTENT_PRIVATE_ITEMS: dict = {
    ContentType.INCIDENT_FIELD: [
        "Employee ID",
        "employeeid",
        "Employee Number",
        "employeenumber",
        "Employee Type",
        "employeetype",
        "Employment Status",
        "employmentstatus",
        "Hire Date",
        "hiredate",
        "Last Day of Work",
        "lastdayofwork",
        "Prehire Flag",
        "prehireflag",
        "Rehired Employee",
        "rehiredemployee",
        "Termination Date",
        "terminationdate",
        "userprofile",
        "organization",
        "actor",
        "Termination Trigger",
        "terminationtrigger",
        "State Name",
        "statename",
        "profileid",
        "timezonesidkey",
        "localesidkey",
    ],
    ContentType.INCIDENT_TYPE: [
        "IAM - AD User Activation",
        "IAM - AD User Deactivation",
        "IAM - New Hire",
        "IAM - Rehire User",
        "IAM - Sync User",
        "IAM - Terminate User",
        "IAM - Update User",
        "User Profile - Create",
        "User Profile - Update",
        "User Profile",
        "IAM - App Add",
        "IAM - Group Membership Update",
        "IAM - App Remove",
        "IAM - App Update",
    ],
    ContentType.SCRIPT: [
        "IAM-Init-AD-User",
    ],
    ContentType.LAYOUT: [
        "MITRE Layout",
    ],
}


def replace_marketplace_references(
    data: Any, marketplace: MarketplaceVersions, path: str = ""
) -> Any:
    """
    Recursively replaces "Cortex XSOAR" with "Cortex" in the given data if the marketplace is MarketplaceV2 or XPANSE.
    If the word following "Cortex XSOAR" contains a number, it will also be removed.
    The replacement will be skipped if "https" appears within 20 characters after "Cortex XSOAR." This ensures that documentation with distinct links for different products or versions remains unchanged. see CIAC-12049 for details.

    Args:
        data (Any): The data to process, which can be a dictionary, list, or string.
        marketplace (MarketplaceVersions): The marketplace version to check against.
        path (str): The path of the item being processed.

    Returns:
        Any: The same data object with replacements made if applicable.
    """
    pattern = r"\bCortex XSOAR\b(?![\S]*\/)(?:\s+[\w.]*\d[\w.]*)?(?!(?:.{0,20})https)"
    try:
        if marketplace in {
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.XPANSE,
            MarketplaceVersions.PLATFORM,
        }:
            if isinstance(data, dict):
                keys_to_update = {}
                for key, value in data.items():
                    # Process the key
                    new_key = (
                        re.sub(pattern, "Cortex", key) if isinstance(key, str) else key
                    )
                    if new_key != key:
                        keys_to_update[key] = new_key
                    # Process the value
                    data[key] = replace_marketplace_references(value, marketplace, path)
                # Update the keys in the dictionary
                for old_key, new_key in keys_to_update.items():
                    data[new_key] = data.pop(old_key)
            elif isinstance(data, list):
                for i in range(len(data)):
                    data[i] = replace_marketplace_references(data[i], marketplace, path)
            elif isinstance(data, FoldedScalarString):
                # if data is a FoldedScalarString (yml unification), we need to convert it to a string and back
                data = FoldedScalarString(re.sub(pattern, "Cortex", str(data)))
            elif isinstance(data, str):
                data = re.sub(pattern, "Cortex", data)
    except Exception as e:
        logger.error(
            f"Error processing data for replacing incorrect marketplace at path '{path}': {e}"
        )
    return data


def append_supported_modules(
    data: dict,
    supported_modules: Optional[List[str]],
    pack_supported_modules: Optional[List[str]],
) -> Any:
    """
    Appends the `supportedModules` key & value to the data object if it doesn't already exist.

    Args:
        data (dict): The data to process.
        supported_modules (List[str]): The list of supported modules.

    Returns:
        Any: The same data object with supported modules appended.
    """
    if not supported_modules and "supportedModules" in data:
        del data["supportedModules"]
        return data

    if pack_supported_modules and supported_modules:
        for module in pack_supported_modules:
            if module not in supported_modules:
                return data

        if "supportedModules" in data:
            del data["supportedModules"]
    return data

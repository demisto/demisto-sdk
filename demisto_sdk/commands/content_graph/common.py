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
    PACKS_FOLDER,
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

    @classmethod
    def by_path(cls, path: Path) -> "ContentType":
        for idx, folder in enumerate(path.parts):
            if folder == PACKS_FOLDER:
                if len(path.parts) <= idx + 2:
                    raise ValueError("Invalid content path.")
                content_type_dir = path.parts[idx + 2]
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
        normalized_header = header.rstrip("s").replace(" ", "_").upper()
        return ContentType[normalized_header]


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
        content_type: ContentType = ContentType(kwargs.get("content_type"))
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


def append_supported_modules(data: dict, supported_modules: List[str]) -> Any:
    """
    Appends the `supportedModules` key & value to the data object if it doesn't already exist.

    Args:
        data (dict): The data to process.
        supported_modules (List[str]): The list of supported modules.

    Returns:
        Any: The same data object with supported modules appended.
    """

    if isinstance(data, dict):
        if "supportedModules" not in data:
            data["supportedModules"] = supported_modules
    return data

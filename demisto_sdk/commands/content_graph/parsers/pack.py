import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.common import (
    PACK_CONTRIBUTORS_FILENAME,
    PACK_METADATA_FILENAME,
    ContentType,
    Relationships,
    RelationshipType,
)
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser
from demisto_sdk.commands.content_graph.parsers.content_item import (
    ContentItemParser,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.content_items_list import (
    ContentItemsList,
)

logger = logging.getLogger("demisto-sdk")


class PackContentItems:
    """A class that holds all pack's content items in lists by their types."""

    def __init__(self) -> None:
        self.classifier = ContentItemsList(content_type=ContentType.CLASSIFIER)
        self.correlation_rule = ContentItemsList(
            content_type=ContentType.CORRELATION_RULE
        )
        self.dashboard = ContentItemsList(content_type=ContentType.DASHBOARD)
        self.generic_definition = ContentItemsList(
            content_type=ContentType.GENERIC_DEFINITION
        )
        self.generic_field = ContentItemsList(content_type=ContentType.GENERIC_FIELD)
        self.generic_module = ContentItemsList(content_type=ContentType.GENERIC_MODULE)
        self.generic_type = ContentItemsList(content_type=ContentType.GENERIC_TYPE)
        self.incident_field = ContentItemsList(content_type=ContentType.INCIDENT_FIELD)
        self.incident_type = ContentItemsList(content_type=ContentType.INCIDENT_TYPE)
        self.indicator_field = ContentItemsList(
            content_type=ContentType.INDICATOR_FIELD
        )
        self.indicator_type = ContentItemsList(content_type=ContentType.INDICATOR_TYPE)
        self.integration = ContentItemsList(content_type=ContentType.INTEGRATION)
        self.job = ContentItemsList(content_type=ContentType.JOB)
        self.layout = ContentItemsList(content_type=ContentType.LAYOUT)
        self.list = ContentItemsList(content_type=ContentType.LIST)
        self.mapper = ContentItemsList(content_type=ContentType.MAPPER)
        self.modeling_rule = ContentItemsList(content_type=ContentType.MODELING_RULE)
        self.parsing_rule = ContentItemsList(content_type=ContentType.PARSING_RULE)
        self.playbook = ContentItemsList(content_type=ContentType.PLAYBOOK)
        self.report = ContentItemsList(content_type=ContentType.REPORT)
        self.script = ContentItemsList(content_type=ContentType.SCRIPT)
        self.test_playbook = ContentItemsList(content_type=ContentType.TEST_PLAYBOOK)
        self.trigger = ContentItemsList(content_type=ContentType.TRIGGER)
        self.widget = ContentItemsList(content_type=ContentType.WIDGET)
        self.wizard = ContentItemsList(content_type=ContentType.WIZARD)
        self.xsiam_dashboard = ContentItemsList(
            content_type=ContentType.XSIAM_DASHBOARD
        )
        self.xsiam_report = ContentItemsList(content_type=ContentType.XSIAM_REPORT)
        self.xdrc_template = ContentItemsList(content_type=ContentType.XDRC_TEMPLATE)
        self.layout_rule = ContentItemsList(content_type=ContentType.LAYOUT_RULE)

    def iter_lists(self) -> Iterator[ContentItemsList]:
        yield from vars(self).values()

    def append(self, obj: ContentItemParser) -> None:
        """Appends a content item by iterating the content item lists
        until the correct list is found, and appends to it.

        Args:
            obj (ContentItemParser): The conten item to append.

        Raises:
            NotAContentItemException: If did not find any matching content item list.
        """
        for content_item_list in self.iter_lists():
            try:
                content_item_list.append(obj)
                break
            except TypeError:
                continue
        else:
            raise NotAContentItemException


class PackMetadataParser:
    """A pack metadata parser."""

    def __init__(self, metadata: Dict[str, Any]) -> None:
        self.name: str = metadata["name"]
        self.description: str = metadata["description"]
        self.created: str = metadata.get("created", "")
        self.updated: str = metadata.get("updated", "")
        self.support: str = metadata["support"]
        self.email: str = metadata.get("email", "")
        self.url: str = metadata["url"]
        self.author: str = metadata["author"]
        self.certification: str = (
            "certified" if self.support.lower() in ["xsoar", "partner"] else ""
        )
        self.hidden: bool = metadata.get("hidden", False)
        self.server_min_version: str = metadata.get("serverMinVersion", "")
        self.current_version: str = metadata["currentVersion"]
        self.tags: List[str] = metadata["tags"]
        self.categories: List[str] = metadata["categories"]
        self.use_cases: List[str] = metadata["useCases"]
        self.keywords: List[str] = metadata["keywords"]
        self.price: Optional[int] = metadata.get("price")
        self.premium: Optional[bool] = metadata.get("premium")
        self.vendor_id: Optional[str] = metadata.get("vendorId")
        self.vendor_name: Optional[str] = metadata.get("vendorName")
        self.preview_only: Optional[bool] = metadata.get("previewOnly")
        self.marketplaces: List[MarketplaceVersions] = metadata.get(
            "marketplaces", list(MarketplaceVersions)
        )
        self.excluded_dependencies: List[str] = metadata.get("excludedDependencies", [])


class PackParser(BaseContentParser, PackMetadataParser):
    """A parsed representation of a pack.

    Attributes:
        marketplaces (List[MarketplaceVersions]): The marketplaces supporting this pack.
        content_items (PackContentItems): A collection of this pack's content item parsers.
        relationships (Relationships): A collection of the relationships in this pack.
    """

    content_type = ContentType.PACK

    def __init__(self, path: Path) -> None:
        """Parses a pack and its content items.

        Args:
            path (Path): The pack path.
        """
        BaseContentParser.__init__(self, path)
        metadata = get_json(path / PACK_METADATA_FILENAME)
        PackMetadataParser.__init__(self, metadata)
        self.content_items: PackContentItems = PackContentItems()
        self.relationships: Relationships = Relationships()
        self.connect_pack_dependencies(metadata)
        try:
            self.contributors: List[str] = get_json(path / PACK_CONTRIBUTORS_FILENAME)
        except FileNotFoundError:
            logger.debug(f"No contributors file found in {path}")
        logger.info(f"Parsing {self.node_id}")
        self.parse_pack_folders()
        logger.debug(f"Successfully parsed {self.node_id}")

    @property
    def object_id(self) -> Optional[str]:
        return self.path.name

    def connect_pack_dependencies(self, metadata: Dict[str, Any]) -> None:
        dependency: Dict[str, Dict[str, Any]]
        for pack_id, dependency in metadata.get("dependencies", {}).items():
            self.relationships.add(
                RelationshipType.DEPENDS_ON,
                source=self.object_id,
                target=pack_id,
                mandatorily=dependency.get("mandatory"),
            )

    def parse_pack_folders(self) -> None:
        """Parses all pack content items by iterating its folders."""
        for folder_path in ContentType.pack_folders(self.path):
            for (
                content_item_path
            ) in folder_path.iterdir():  # todo: consider multiprocessing
                self.parse_content_item(content_item_path)

    def parse_content_item(self, content_item_path: Path) -> None:
        """Potentially parses a single content item.

        Args:
            content_item_path (Path): The content item path.
        """
        if content_item := ContentItemParser.from_path(
            content_item_path, self.marketplaces
        ):
            content_item.add_to_pack(self.object_id)
            self.content_items.append(content_item)
            self.relationships.update(content_item.relationships)

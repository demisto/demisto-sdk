from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import regex

from demisto_sdk.commands.common.constants import (
    BASE_PACK,
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
    PACK_NAME_DEPRECATED_REGEX,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import capital_case, get_json
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
    InvalidContentItemException,
    NotAContentItemException,
)
from demisto_sdk.commands.content_graph.parsers.content_items_list import (
    ContentItemsList,
)

DEFAULT_MARKETPLACES = [
    MarketplaceVersions.XSOAR.value,
    MarketplaceVersions.MarketplaceV2.value,
]


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
        self.preprocess_rule = ContentItemsList(
            content_type=ContentType.PREPROCESS_RULE
        )

    def iter_lists(self) -> Iterator[ContentItemsList]:
        yield from vars(self).values()

    def append(self, obj: ContentItemParser) -> None:
        """
        Appends the object to the list with the same content_type.

        Args:
            obj (ContentItemParser): The content item to append.

        Raises:
            NotAContentItemException: If did not find any matching content item list.
        """
        for item_list in self.iter_lists():
            if item_list.content_type == obj.content_type:
                item_list.append(obj)
                return

        raise NotAContentItemException(
            f"Could not find list of {obj.content_type} items"
        )


NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


class PackMetadataParser:
    """A pack metadata parser."""

    def __init__(self, path: Path, metadata: Dict[str, Any]) -> None:
        self.name: str = metadata["name"]
        self.description: str = metadata["description"]
        self.created: str = metadata.get("created") or NOW
        self.updated: str = metadata.get("updated") or NOW
        self.legacy: bool = metadata.get(
            "legacy", metadata.get("partnerId") is None
        )  # default: True, private default: False
        self.support: str = metadata["support"]
        self.email: str = metadata.get("email") or ""
        self.eulaLink: str = (
            metadata.get("eulaLink")
            or "https://github.com/demisto/content/blob/master/LICENSE"
        )
        self.author_image: str = self.get_author_image_filepath(path=path)
        self.price: int = int(metadata.get("price") or 0)
        self.hidden: bool = metadata.get("hidden", False)
        self.server_min_version: str = metadata.get("serverMinVersion", "")
        self.current_version: str = metadata.get("currentVersion", "")
        self.version_info: str = ""
        self.commit: str = GitUtil().get_current_commit_hash() or ""
        self.downloads: int = 0
        self.tags: List[str] = metadata.get("tags") or []
        self.keywords: List[str] = metadata["keywords"] or []
        self.search_rank: int = 0
        self.videos: List[str] = metadata.get("videos", [])
        self.marketplaces: List[str] = (
            metadata.get("marketplaces") or DEFAULT_MARKETPLACES
        )
        if MarketplaceVersions.XSOAR.value in self.marketplaces:
            # Since we want xsoar-saas and xsoar to contain the same content items.
            self.marketplaces.append(MarketplaceVersions.XSOAR_SAAS.value)

        if MarketplaceVersions.XSOAR_ON_PREM.value in self.marketplaces:
            self.marketplaces.append(MarketplaceVersions.XSOAR.value)

        marketplaces_set = set(self.marketplaces)
        self.marketplaces = sorted(marketplaces_set)

        self.excluded_dependencies: List[str] = metadata.get("excludedDependencies", [])
        self.modules: List[str] = metadata.get("modules", [])
        self.integrations: List[str] = []

        # For private packs
        self.premium: Optional[bool] = "partnerId" in metadata
        self.vendor_id: Optional[str] = metadata.get("vendorId") or ""
        self.partner_id: Optional[str] = metadata.get("partnerId") or ""
        self.partner_name: Optional[str] = metadata.get("partnerName") or ""
        self.preview_only: Optional[bool] = metadata.get("previewOnly") or False
        self.disable_monthly: Optional[bool] = metadata.get("disableMonthly") or False
        self.content_commit_hash: Optional[str] = (
            metadata.get("contentCommitHash") or ""
        )

        self.pack_metadata: dict = metadata

    @property
    def url(self) -> str:
        if "url" in self.pack_metadata and self.pack_metadata["url"]:
            return self.pack_metadata.get("url", "")
        return (
            "https://www.paloaltonetworks.com/cortex" if self.support == "xsoar" else ""
        )

    @property
    def certification(self):
        if self.support in ["xsoar", "partner"]:
            return "certified"
        return self.pack_metadata.get("certification") or ""

    @property
    def author(self):
        return (
            self.pack_metadata.get(
                "author", "Cortex XSOAR" if self.support == "xsoar" else ""
            )
            or ""
        )

    @property
    def categories(self):
        return [capital_case(c) for c in self.pack_metadata["categories"]]

    @property
    def use_cases(self):
        return [capital_case(c) for c in self.pack_metadata["useCases"]]

    def get_author_image_filepath(self, path: Path) -> str:
        if (path / "Author_image.png").is_file():
            return f"content/packs/{path.name}/Author_image.png"
        elif self.support == "xsoar":
            return "content/packs/Base/Author_image.png"
        return ""


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

        try:
            metadata = get_json(path / PACK_METADATA_FILENAME)
        except FileNotFoundError:
            raise NotAContentItemException(
                f"{PACK_METADATA_FILENAME} not found in pack in {path=}"
            )

        PackMetadataParser.__init__(self, path, metadata)

        self.content_items: PackContentItems = PackContentItems()
        self.relationships: Relationships = Relationships()
        self.connect_pack_dependencies(metadata)
        try:
            self.contributors: List[str] = get_json(path / PACK_CONTRIBUTORS_FILENAME)
        except FileNotFoundError:
            logger.debug(f"No contributors file found in {path}")
        logger.debug(f"Parsing {self.node_id}")
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

        if (
            self.object_id != BASE_PACK
        ):  # add Base pack dependency for all the packs except Base itself
            self.relationships.add(
                RelationshipType.DEPENDS_ON,
                source=self.object_id,
                target=BASE_PACK,
                mandatorily=True,
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
        try:
            content_item = ContentItemParser.from_path(
                content_item_path, [MarketplaceVersions(mp) for mp in self.marketplaces]
            )
            content_item.add_to_pack(self.object_id)
            self.content_items.append(content_item)
            self.relationships.update(content_item.relationships)
        except NotAContentItemException:
            logger.debug(f"Skipping {content_item_path} - not a content item")
        except InvalidContentItemException:
            logger.error(f"{content_item_path} - invalid content item")
            raise

    @property
    def deprecated(self) -> bool:
        if regex.match(PACK_NAME_DEPRECATED_REGEX, self.name) and (
            regex.match(DEPRECATED_NO_REPLACE_DESC_REGEX, self.description)
            or regex.match(DEPRECATED_DESC_REGEX, self.description)
        ):
            return True
        return False

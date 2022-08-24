import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.common import (
    ContentTypes,
    PACK_METADATA_FILENAME,
    Relationships
)
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser, NotAContentItem


logger = logging.getLogger('demisto-sdk')


class ContentItemsList(list):
    """ An extension for list - a list of a specific content type.

    Attributes:
        content_type (ContentTypes): The content types allowed to be included in this list.
    """
    def __init__(self, content_type: ContentTypes):
        self.content_type: ContentTypes = content_type
        super().__init__()

    def append_conditionally(self, content_item: ContentItemParser) -> bool:
        """ Appends if the content item is in the correct type.

        Args:
            content_item (ContentItemParser): The content item.

        Returns:
            bool: True iff the content item was appended.
        """
        if isinstance(content_item, ContentItemParser) and content_item.content_type == self.content_type:
            self.append(content_item)
            return True
        return False


class PackContentItems:
    """ A class that holds all pack's content items in lists by their types.
    """
    def __init__(self) -> None:
        self.classifier = ContentItemsList(content_type=ContentTypes.CLASSIFIER)
        self.correlation_rule = ContentItemsList(content_type=ContentTypes.CORRELATION_RULE)
        self.dashboard = ContentItemsList(content_type=ContentTypes.DASHBOARD)
        self.generic_definition = ContentItemsList(content_type=ContentTypes.GENERIC_DEFINITION)
        self.generic_module = ContentItemsList(content_type=ContentTypes.GENERIC_MODULE)
        self.generic_type = ContentItemsList(content_type=ContentTypes.GENERIC_TYPE)
        self.incident_field = ContentItemsList(content_type=ContentTypes.INCIDENT_FIELD)
        self.incident_type = ContentItemsList(content_type=ContentTypes.INCIDENT_TYPE)
        self.indicator_field = ContentItemsList(content_type=ContentTypes.INDICATOR_FIELD)
        self.indicator_type = ContentItemsList(content_type=ContentTypes.INDICATOR_TYPE)
        self.integration = ContentItemsList(content_type=ContentTypes.INTEGRATION)
        self.job = ContentItemsList(content_type=ContentTypes.JOB)
        self.layout = ContentItemsList(content_type=ContentTypes.LAYOUT)
        self.list = ContentItemsList(content_type=ContentTypes.LIST)
        self.mapper = ContentItemsList(content_type=ContentTypes.MAPPER)
        self.modeling_rule = ContentItemsList(content_type=ContentTypes.MODELING_RULE)
        self.parsing_rule = ContentItemsList(content_type=ContentTypes.PARSING_RULE)
        self.playbook = ContentItemsList(content_type=ContentTypes.PLAYBOOK)
        self.report = ContentItemsList(content_type=ContentTypes.REPORT)
        self.script = ContentItemsList(content_type=ContentTypes.SCRIPT)
        self.test_playbook = ContentItemsList(content_type=ContentTypes.TEST_PLAYBOOK)
        self.trigger = ContentItemsList(content_type=ContentTypes.TRIGGER)
        self.widget = ContentItemsList(content_type=ContentTypes.WIDGET)
        self.wizard = ContentItemsList(content_type=ContentTypes.WIZARD)
        self.xsiam_dashboard = ContentItemsList(content_type=ContentTypes.XSIAM_DASHBOARD)
        self.xsiam_report = ContentItemsList(content_type=ContentTypes.XSIAM_REPORT)

    def iter_lists(self) -> Iterator[ContentItemsList]:
        for attribute in vars(self).values():
            yield attribute

    def append(self, obj: ContentItemParser) -> None:
        """ Appends a content item by iterating the content item lists
        until finds the correct list and appends to it.

        Args:
            obj (ContentItemParser): The conten item to append.

        Raises:
            NotAContentItem: If did not find any matching content item list.
        """
        for content_item_list in self.iter_lists():
            if content_item_list.append_conditionally(obj):
                break
        else:
            raise NotAContentItem


class PackMetadataParser:
    """ A pack metadata parser.
    """
    def __init__(self, metadata: Dict[str, Any]) -> None:
        self.name: str = metadata['name']
        self.description: str = metadata['description']
        self.created: str = metadata.get('created', '')
        self.updated: str = metadata.get('updated', '')
        self.support: str = metadata['support']
        self.email: str = metadata.get('email', '')
        self.url: str = metadata['url']
        self.author: str = metadata['author']
        self.certification: str = 'certified' if self.support.lower() in ['xsoar', 'partner'] else ''
        self.hidden: bool = metadata.get('hidden', False)
        self.server_min_version: str = metadata.get('serverMinVersion', '')
        self.current_version: str = metadata['currentVersion']
        self.tags: List[str] = metadata['tags']
        self.categories: List[str] = metadata['categories']
        self.use_cases: List[str] = metadata['useCases']
        self.keywords: List[str] = metadata['keywords']
        self.price: Optional[int] = metadata.get('price')
        self.premium: Optional[bool] = metadata.get('premium')
        self.vendor_id: Optional[str] = metadata.get('vendorId')
        self.vendor_name: Optional[str] = metadata.get('vendorName')
        self.preview_only: Optional[bool] = metadata.get('previewOnly')


class PackParser(BaseContentParser, PackMetadataParser):
    """ A parsed representation of a pack.

    Attributes:
        marketplaces (List[MarketplaceVersions]): The marketplaces supporting this pack.
        content_items (PackContentItems): A collection of this pack's content item parsers.
        relationships (Relationships): A collection of the relationships in this pack.
    """
    def __init__(self, path: Path) -> None:
        """ Parses a pack and its content items.

        Args:
            path (Path): The pack path.
        """
        BaseContentParser.__init__(self, path)
        metadata: Dict[str, Any] = get_json(path / PACK_METADATA_FILENAME)
        PackMetadataParser.__init__(self, metadata)
        self.marketplaces = metadata.get('marketplaces', list(MarketplaceVersions))
        self.content_items: PackContentItems = PackContentItems()
        self.relationships: Relationships = Relationships()
        self.parse_pack_folders()
        logger.info(f'Parsed {self.node_id}')

    @property
    def object_id(self) -> str:
        return self.path.name

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.PACK

    def parse_pack_folders(self) -> None:
        """ Parses all pack content items by iterating its folders.
        """
        for folder_path in ContentTypes.pack_folders(self.path):
            for content_item_path in folder_path.iterdir():  # todo: consider multiprocessing
                self.parse_content_item(content_item_path)

    def parse_content_item(self, content_item_path: Path) -> None:
        """ Potentially parses a single content item.

        Args:
            content_item_path (Path): The content item path.
        """
        if content_item := ContentItemParser.from_path(content_item_path):
            content_item.add_to_pack(self.node_id)
            self.content_items.append(content_item)
            self.relationships.update(content_item.relationships)

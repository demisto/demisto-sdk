import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.content_graph.constants import (
    ContentTypes,
    PACK_METADATA_FILENAME,
    Relationships
)
from demisto_sdk.commands.content_graph.parsers.base_content import BaseContentParser
from demisto_sdk.commands.content_graph.parsers.content_item import ContentItemParser

logger = logging.getLogger('demisto-sdk')

class PackContentItems:
    def __init__(self) -> None:
        self.classifier: List[ContentItemParser] = []
        self.correlation_rule: List[ContentItemParser] = []
        self.dashboard: List[ContentItemParser] = []
        self.generic_definition: List[ContentItemParser] = []
        self.generic_module: List[ContentItemParser] = []
        self.generic_type: List[ContentItemParser] = []
        self.incident_field: List[ContentItemParser] = []
        self.incident_type: List[ContentItemParser] = []
        self.indicator_field: List[ContentItemParser] = []
        self.indicator_type: List[ContentItemParser] = []
        self.integration: List[ContentItemParser] = []
        self.job: List[ContentItemParser] = []
        self.layout: List[ContentItemParser] = []
        self.list: List[ContentItemParser] = []
        self.mapper: List[ContentItemParser] = []
        self.modeling_rule: List[ContentItemParser] = []
        self.parsing_rule: List[ContentItemParser] = []
        self.playbook: List[ContentItemParser] = []
        self.report: List[ContentItemParser] = []
        self.script: List[ContentItemParser] = []
        self.test_playbook: List[ContentItemParser] = []
        self.trigger: List[ContentItemParser] = []
        self.widget: List[ContentItemParser] = []
        self.wizard: List[ContentItemParser] = []
        self.xsiam_dashboard: List[ContentItemParser] = []
        self.xsiam_report: List[ContentItemParser] = []
    
    def append(self, obj: ContentItemParser) -> None:
        if obj.content_type == ContentTypes.CLASSIFIER:
            self.classifier.append(obj)
        elif obj.content_type == ContentTypes.CORRELATION_RULE:
            self.correlation_rule.append(obj)
        elif obj.content_type == ContentTypes.DASHBOARD:
            self.dashboard.append(obj)
        elif obj.content_type == ContentTypes.GENERIC_DEFINITION:
            self.generic_definition.append(obj)
        elif obj.content_type == ContentTypes.GENERIC_MODULE:
            self.generic_module.append(obj)
        elif obj.content_type == ContentTypes.GENERIC_TYPE:
            self.generic_type.append(obj)
        elif obj.content_type == ContentTypes.INCIDENT_FIELD:
            self.incident_field.append(obj)
        elif obj.content_type == ContentTypes.INCIDENT_TYPE:
            self.incident_type.append(obj)
        elif obj.content_type == ContentTypes.INDICATOR_FIELD:
            self.indicator_field.append(obj)
        elif obj.content_type == ContentTypes.INDICATOR_TYPE:
            self.indicator_type.append(obj)
        elif obj.content_type == ContentTypes.INTEGRATION:
            self.integration.append(obj)
        elif obj.content_type == ContentTypes.JOB:
            self.job.append(obj)
        elif obj.content_type == ContentTypes.LAYOUT:
            self.layout.append(obj)
        elif obj.content_type == ContentTypes.LIST:
            self.list.append(obj)
        if obj.content_type == ContentTypes.MAPPER:
            self.mapper.append(obj)
        elif obj.content_type == ContentTypes.MODELING_RULE:
            self.modeling_rule.append(obj)
        elif obj.content_type == ContentTypes.PARSING_RULE:
            self.parsing_rule.append(obj)
        elif obj.content_type == ContentTypes.PLAYBOOK:
            self.playbook.append(obj)
        elif obj.content_type == ContentTypes.REPORT:
            self.report.append(obj)
        elif obj.content_type == ContentTypes.SCRIPT:
            self.script.append(obj)
        elif obj.content_type == ContentTypes.TEST_PLAYBOOK:
            self.test_playbook.append(obj)
        elif obj.content_type == ContentTypes.TRIGGER:
            self.trigger.append(obj)
        elif obj.content_type == ContentTypes.WIDGET:
            self.widget.append(obj)
        elif obj.content_type == ContentTypes.WIZARD:
            self.wizard.append(obj)
        elif obj.content_type == ContentTypes.XSIAM_DASHBOARD:
            self.xsiam_dashboard.append(obj)
        elif obj.content_type == ContentTypes.XSIAM_REPORT:
            self.xsiam_report.append(obj)


class PackMetadataParser:
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

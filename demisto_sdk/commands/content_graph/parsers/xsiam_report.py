from pathlib import Path
from typing import List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class XSIAMReportParser(JSONContentItemParser, content_type=ContentType.XSIAM_REPORT):
    def __init__(self, path: Path, pack_marketplaces: List[MarketplaceVersions]) -> None:
        super().__init__(path, pack_marketplaces)
        self.json_data = self.json_data.get('templates_data', [{}])[0]

    @property
    def name(self) -> str:
        return self.json_data['report_name']

    @property
    def object_id(self) -> str:
        return self.json_data['global_id']

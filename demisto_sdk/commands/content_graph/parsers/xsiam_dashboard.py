from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class XSIAMDashboardParser(JSONContentItemParser, content_type=ContentType.XSIAM_DASHBOARD):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.json_data = self.json_data.get('dashboards_data', [{}])[0]

    @property
    def object_id(self) -> str:
        return self.json_data['global_id']

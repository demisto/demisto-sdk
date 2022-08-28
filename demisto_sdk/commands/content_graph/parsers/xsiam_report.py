from pathlib import Path

from demisto_sdk.commands.content_graph.common import ContentTypes
from demisto_sdk.commands.content_graph.parsers.json_content_item import JSONContentItemParser


class XSIAMReportParser(JSONContentItemParser, content_type=ContentTypes.XSIAM_REPORT):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.json_data = self.json_data.get('templates_data', [{}])[0]

    @property
    def name(self) -> str:
        return self.json_data['report_name']

    @property
    def object_id(self) -> str:
        return self.json_data['global_id']

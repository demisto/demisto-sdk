from pathlib import Path

from demisto_sdk.commands.content_graph.constants import ContentTypes
from demisto_sdk.commands.content_graph.parsers.content_item import JSONContentItemParser


class XSIAMReportParser(JSONContentItemParser):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        print(f'Parsing {self.content_type} {self.object_id}')
        self.json_data = self.json_data.get('templates_data', [{}])[0]

    @property
    def content_type(self) -> ContentTypes:
        return ContentTypes.XSIAM_REPORT

    @property
    def name(self) -> str:
        return self.json_data['report_name']

    @property
    def object_id(self) -> str:
        return self.json_data['global_id']

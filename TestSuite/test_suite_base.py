from pathlib import Path

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent


class TestSuiteBase:
    def __init__(self, path: Path):
        self.obj_path = path
    
    @property
    def object(self):
        return BaseContent.from_path(self.obj_path)

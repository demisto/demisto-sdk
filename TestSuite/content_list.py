from pathlib import Path

from TestSuite.json_based import JSONBased


class ContentList(JSONBased):
    def __init__(self, name: str, list_dir_path: Path, json_content: dict = None):
        self.list_tmp_path = list_dir_path / f"{name}.json"
        super().__init__(dir_path=list_dir_path, name=name, prefix="", json_content=json_content)

    def create_default(self):
        self.write_json(
            {
                "allRead": True,
                "allReadWrite": True,
                "data": "test line 1\ntest_line_2",
                "id": self.id,
                "itemVersion": "",
                "locked": False,
                "name": self.id,
                "nameLocked": False,
                "packID": "",
                "previousAllRead": True,
                "system": True,
                "truncated": False,
                "type": "plain_text",
                "version": -1,
                "fromVersion": "6.10.0",
                "marketplaces": [
                    "xsoar"
                ]
            }
        )

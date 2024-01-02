from pathlib import Path

from TestSuite.json_based import JSONBased


class Dashboard(JSONBased):
    def __init__(self, name: str, dashboard_dir_path: Path, json_content: dict = None):
        self.dashboard_tmp_path = dashboard_dir_path / f"{name}.json"
        super().__init__(
            dir_path=dashboard_dir_path, name=name, prefix="", json_content=json_content
        )

    def create_default(self):
        self.write_json(
            {
                "id": self.name,
                "packID": "",
                "packName": "",
                "name": self.name,
                "prevName": self.name,
                "layout": [],
                "owner": "admin",
            }
        )

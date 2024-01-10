from pathlib import Path

from TestSuite.json_based import JSONBased


class Layout(JSONBased):
    def __init__(self, name: str, layout_dir_path: Path, json_content: dict = None):
        self.layout_rule_tmp_path = layout_dir_path / f"{name}.json"
        super().__init__(dir_path=layout_dir_path, name=name, prefix="", json_content=json_content)

    def create_default(self):
        self.write_json(
            {
                "detailsV2": {
                    "tabs": [
                        {"id": "warRoom", "name": "War Room", "type": "warRoom"},
                        {"id": "workPlan", "name": "Work Plan", "type": "workPlan"},
                    ]
                },
                "group": "incident",
                "id": self.id,
                "name": "TestDefault",
                "quickView": {"sections": []},
                "system": False,
                "version": -1,
                "fromVersion": "6.8.0",
                "description": "TestDefaultDescription",
            }
        )

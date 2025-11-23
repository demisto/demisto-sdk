from pathlib import Path

from TestSuite.json_based import JSONBased


class LayoutRule(JSONBased):
    def __init__(
        self, name: str, layout_rule_dir_path: Path, json_content: dict = None
    ):
        self.layout_rule_tmp_path = layout_rule_dir_path / f"{name}.json"
        self.name = name
        self.rule_id = name

        super().__init__(dir_path=layout_rule_dir_path, name=name, prefix="")

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_layout_rule()

    def create_default_layout_rule(self):
        self.write_json(
            {
                "id": self.rule_id,
                "name": self.name,
                "layout_id": "test_layout",
                "description": "",
                "alerts_filter": {
                    "filter": {
                        "AND": [
                            {
                                "SEARCH_FIELD": "alert_type",
                                "SEARCH_TYPE": "EQ",
                                "SEARCH_VALUE": "test",
                            }
                        ]
                    }
                },
                "fromVersion": "6.10.0",
            }
        )

from pathlib import Path

from TestSuite.json_based import JSONBased


class CaseLayoutRule(JSONBased):
    def __init__(
        self, name: str, case_layout_rule_dir_path: Path, json_content: dict = None
    ):
        self.layout_rule_tmp_path = case_layout_rule_dir_path / f"{name}.json"
        self.name = name
        self.rule_id = name

        super().__init__(dir_path=case_layout_rule_dir_path, name=name, prefix="")

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_case_layout_rule()

    def create_default_case_layout_rule(self):
        self.write_json(
            {
                "rule_id": self.rule_id,
                "rule_name": self.rule_id,
                "layout_id": "test_layout",
                "description": "",
                "incidents_filter": {
                    "filter": {
                        "AND": [
                            {
                                "SEARCH_FIELD": "STATUS",
                                "SEARCH_TYPE": "NEQ",
                                "SEARCH_VALUE": "STATUS_030_RESOLVED_THREAT_HANDLED",
                            }
                        ]
                    }
                },
                "fromVersion": "8.7.0",
            }
        )

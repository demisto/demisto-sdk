from pathlib import Path

from TestSuite.json_based import JSONBased


class CaseLayout(JSONBased):
    def __init__(
        self, name: str, case_layout_dir_path: Path, json_content: dict = None
    ):
        self.case_layout_tmp_path = case_layout_dir_path / f"{name}.json"
        super().__init__(
            dir_path=case_layout_dir_path,
            name=name,
            prefix="layoutcontainer",
            json_content=json_content,
        )

    def create_default(self):
        self.write_json(
            {
                "detailsV2": {
                    "tabs": [
                        {"id": "overview", "name": "Overview", "type": "overview"},
                        {
                            "id": "alerts_and_insights",
                            "name": "Alerts \u0026 Insights",
                            "type": "alertInsights",
                        },
                        {"id": "timeline", "name": "Timeline", "type": "timeline"},
                        {
                            "id": "executions",
                            "name": "Executions",
                            "type": "executions",
                        },
                    ]
                },
                "group": "case",
                "id": self.id,
                "name": self.id,
                "system": False,
                "version": -1,
                "fromVersion": "8.7.0",
                "description": "",
            }
        )

from pathlib import Path

from TestSuite.json_based import JSONBased


class Widget(JSONBased):
    def __init__(
        self,
        name: str,
        widgets_dir_path: Path,
        content: dict
    ):
        super().__init__(widgets_dir_path, name, "widget", json_content=content)

    def create_default(self):
        self.write_json(
            {
                "id": self.name,
                "version": -1,
                "name": self.name,
                "dataType": "indicators",
                "widgetType": "line",
                "size": 1000,
                "query": "",
                "isPredefined": True,
                "dateRange": {
                    "fromDate": "0001-01-01T00:00:00Z",
                    "toDate": "0001-01-01T00:00:00Z",
                    "period": {
                        "byTo": "",
                        "byFrom": "days",
                        "toValue": None,
                        "fromValue": 7,
                        "field": "",
                    },
                },
                "params": {"groupBy": ["calculatedTime"]},
                "description": "",
                "fromVersion": "6.8.0",
            }
        )



from pathlib import Path

from TestSuite.json_based import JSONBased


class XSIAMDashboard(JSONBased):
    def __init__(
        self, name: str, xsiam_dashboard_dir_path: Path, json_content: dict = None
    ):
        self.xsiam_dashboard_tmp_path = xsiam_dashboard_dir_path / f"{name}.json"
        self.name = name

        super().__init__(xsiam_dashboard_dir_path, name, "", json_content)

    def create_default(self):
        self.write_json(
            {
                "dashboards_data": [
                    {
                        "id": self.id,
                        "name": self.id,
                        "description": "mock dashboard desc",
                        "status": "ENABLED",
                        "layout": [
                            {
                                "id": "row-1768",
                                "data": [
                                    {
                                        "key": "xql_1668676732415",
                                        "data": {
                                            "type": "Custom XQL",
                                            "width": 50,
                                            "height": 434,
                                            "phrase": 'datamodel \r\n|filter xdm.observer.vendor="mock vendor"',
                                            "time_frame": {"relativeTime": 2592000000},
                                            "viewOptions": {
                                                "type": "map",
                                                "commands": [
                                                    {
                                                        "command": {
                                                            "op": "=",
                                                            "name": "header",
                                                            "value": '"Cloud Regions"',
                                                        }
                                                    }
                                                ],
                                            },
                                        },
                                    },
                                ],
                            },
                        ],
                        "default_dashboard_id": 1,
                        "global_id": "f9c52470483a41e4a6afa65c93f70a4b",
                        "metadata": {},
                    }
                ],
                "widgets_data": [
                    {
                        "widget_key": "xql_1668676732415",
                        "title": "mock widget",
                        "creation_time": 1668676732415,
                        "description": "mock widget desc",
                        "data": {
                            "phrase": 'datamodel \r\n|filter xdm.observer.vendor="mock vendor"',
                            "time_frame": {"relativeTime": 2592000000},
                            "viewOptions": {
                                "type": "map",
                                "commands": [
                                    {
                                        "command": {
                                            "op": "=",
                                            "name": "header",
                                            "value": '"Cloud Regions"',
                                        }
                                    }
                                ],
                            },
                        },
                        "support_time_range": True,
                        "additional_info": {
                            "query_tables": [],
                            "query_uses_library": False,
                        },
                    },
                ],
            }
        )

from pathlib import Path

from TestSuite.json_based import JSONBased


class XSIAMReport(JSONBased):
    def __init__(
        self, name: str, xsiam_report_dir_path: Path, json_content: dict = None
    ):
        self.xsiam_report_tmp_path = xsiam_report_dir_path / f"{name}.json"
        self.name = name

        super().__init__(xsiam_report_dir_path, name, "", json_content)

    def create_default(self):
        self.write_json(
            {
                "templates_data": [
                    {
                        "global_id": self.id,
                        "report_name": self.id,
                        "report_description": None,
                        "default_template_id": None,
                        "time_frame": {"relativeTime": 86400000},
                        "time_offset": 7200,
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
                    }
                ],
                "widgets_data": [],
            }
        )

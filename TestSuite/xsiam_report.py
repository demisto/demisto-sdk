from pathlib import Path

from TestSuite.json_based import JSONBased


class XSIAMReport(JSONBased):
    def __init__(self, name: str, xsiam_report_dir_path: Path, json_content: dict = {}):
        self.xsiam_report_tmp_path = xsiam_report_dir_path / f"{name}.json"
        self.name = name

        super().__init__(xsiam_report_dir_path, name, '')

        if json_content:
            self.write_json(json_content)
        else:
            self.create_default_xsiam_report()

    def create_default_xsiam_report(self):
        self.write_json({
            "templates_data": [
                {
                    "global_id": self.name,
                    "name": self.name
                }
            ]
        })

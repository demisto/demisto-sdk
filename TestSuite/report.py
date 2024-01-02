import json
from pathlib import Path

from TestSuite.json_based import JSONBased
from TestSuite.test_tools import suite_join_path


class Report(JSONBased):
    def __init__(self, name: str, report_dir_path: Path, json_content: dict = None):
        self.report_tmp_path = report_dir_path / f"{name}.json"

        super().__init__(report_dir_path, name, "", json_content=json_content)

    def create_default(self):
        self.write_json(
            {
                "decoder": {},
                "nextScheduledTime": "0001-01-01T00:00:00Z",
                "latestScheduledReportTime": "0001-01-01T00:00:00Z",
                "latestReportTime": "0001-01-01T00:00:00Z",
                "name": self.name,
                "sections": [],
                "type": "pdf",
                "id": self.name,
                "fromVersion": "6.10.0",
                "description": "Default test report description.",
            }
        )

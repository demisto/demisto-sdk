from pathlib import Path
from typing import Dict, List, Optional

from demisto_sdk.commands.common.handlers import JSON_Handler

json = JSON_Handler()


class ConfJSON:
    def __init__(self, dir_path: Path, name: str, prefix: str):
        self._dir_path = dir_path
        self.name = f'{prefix.rstrip("-")}-{name}'
        self._file_path = dir_path / name
        self.path = str(self._file_path)
        self.write_json()

    def write_json(
        self,
        tests: Optional[List[dict]] = None,
        skipped_tests: Optional[Dict[str, str]] = None,
        skipped_integrations: Optional[Dict[str, str]] = None,
        docker_thresholds: Optional[dict] = None,
    ):
        if tests is None:
            tests = []
        if skipped_tests is None:
            skipped_tests = {}
        if skipped_integrations is None:
            skipped_integrations = {}
        if docker_thresholds is None:
            docker_thresholds = {"_comment": "", "images": []}
        self._file_path.write_text(
            json.dumps(
                {
                    "tests": tests,
                    "skipped_tests": skipped_tests,
                    "skipped_integrations": skipped_integrations,
                    "docker_thresholds": docker_thresholds,
                    # the next fields are not modified in tests (hence lack of args), but are structurally required.
                    "available_tests_fields": [],
                    "testTimeout": 100,
                    "testInterval": 100,
                    "nightly_packs": [],
                    "parallel_integrations": [],
                    "private_tests": [],
                    "test_marketplacev2": [],
                    "reputation_tests": [],
                }
            ),
            None,
        )

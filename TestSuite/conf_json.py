import json
from pathlib import Path
from typing import List, Optional


class ConfJSON:
    def __init__(self, dir_path: Path, name: str, prefix: str):
        self._dir_path = dir_path
        self.name = f'{prefix.rstrip("-")}-{name}'
        self._file_path = dir_path / name
        self.path = str(self._file_path)
        self.write_json()

    def write_json(
            self,
            tests: Optional[List[str]] = None,
            skipped_tests: Optional[List[str]] = None,
            skipped_integrations: Optional[List[str]] = None,
            nightly_integrations: Optional[List[str]] = None,
            unmockable_integrations: Optional[List[str]] = None,
            docker_thresholds: Optional[dict] = None
    ):
        if tests is None:
            tests = []
        if skipped_tests is None:
            skipped_tests = None
        if skipped_integrations is None:
            skipped_integrations = []
        if nightly_integrations is None:
            nightly_integrations = []
        if unmockable_integrations is None:
            unmockable_integrations = []
        if docker_thresholds is None:
            docker_thresholds = {}
        self._file_path.write_text(json.dumps({
            'tests': tests,
            'skipped_tests': skipped_tests,
            'skipped_integrations': skipped_integrations,
            'nightly_integrations': nightly_integrations,
            'unmockable_integrations': unmockable_integrations,
            'docker_thresholds': docker_thresholds
        }), None)

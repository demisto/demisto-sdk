from typing import List, Optional

from TestSuite.json_based import JSONBased


class ConfJSON(JSONBased):
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
        super().write_json({
            'tests': tests,
            'skipped_tests': skipped_tests,
            'skipped_integrations': skipped_integrations,
            'nightly_integrations': nightly_integrations,
            'unmockable_integrations': unmockable_integrations,
            'docker_thresholds': docker_thresholds
        })

"""
Golden tests for the xsoar-linter rules.

test_files/golden/golden.json holds the expected results for every (sample, settings) case.
The cases were recorded from the former pylint-based xsoar-linter, so they prove the checkers
report exactly what pylint reported: same findings (line, column, code, object, message)
and the same pass / fail outcome.

golden.json is not generated anymore. To add a case, add a sample under test_files/golden/samples/
if needed, and write its expected result by hand. A deliberate behaviour change means editing the
expected result and explaining why in the PR.
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.xsoar_linter.checkers.models import LintSettings
from demisto_sdk.commands.xsoar_linter.checkers.runner import lint_file

GOLDEN_DIR = Path(__file__).parent / "test_files" / "golden"
GOLDEN_SAMPLES_DIR = GOLDEN_DIR / "samples"
json = JSON_Handler()

GOLDEN_CASES: List[Dict[str, Any]] = json.loads(
    (GOLDEN_DIR / "golden.json").read_text()
)


def run_golden_case(sample: str, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Run one golden test case. `sample` is a file name in the golden samples folder."""
    result = lint_file(GOLDEN_SAMPLES_DIR / sample, LintSettings(**settings))
    return {
        "fails": result.fails,
        "findings": [finding.to_dict() for finding in result.findings],
    }


@pytest.mark.parametrize(
    "case", GOLDEN_CASES, ids=[case["id"] for case in GOLDEN_CASES]
)
def test_xsoar_linter_matches_golden(case: Dict[str, Any]):
    """
    Given:
        - A sample python file and the integration / script settings it is linted with
          (support level, script or integration, long running, python 2, yml commands).
        - The expected findings for it, in golden.json.
    When:
        - Running the xsoar-linter on the sample with the same settings.
    Then:
        - It reports exactly the expected findings and the same pass / fail outcome.
    """
    # When
    result = run_golden_case(case["sample"], case["settings"])

    # Then
    assert result["findings"] == case["expected"]["findings"]
    assert result["fails"] == case["expected"]["fails"]

"""
Golden tests for the xsoar-linter rules.

test_files/golden/golden.json holds the results of the pylint-based xsoar-linter for every
(sample, settings) case, recorded by test_files/golden/record_golden.py.
Every engine must reproduce those results exactly: same findings (line, column, code, object, message)
and the same pass / fail outcome.

- engine "pylint": proves golden.json really reflects the current pylint implementation.
- engine "ast": proves the ast implementation matches it (skipped until the ast engine exists).
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.xsoar_linter.checkers.runner import run_golden_case

GOLDEN_DIR = Path(__file__).parent / "test_files" / "golden"
json = JSON_Handler()

GOLDEN_CASES: List[Dict[str, Any]] = json.loads(
    (GOLDEN_DIR / "golden.json").read_text()
)


@pytest.mark.parametrize(
    "case", GOLDEN_CASES, ids=[case["id"] for case in GOLDEN_CASES]
)
def test_xsoar_linter_matches_golden(case: Dict[str, Any]):
    """
    Given:
        - A sample python file and the integration / script settings it is linted with
          (support level, script or integration, long running, python 2, yml commands).
        - The findings the pylint-based xsoar-linter reported for it, recorded in golden.json.
    When:
        - Running the xsoar-linter on the sample with the same settings.
    Then:
        - It reports exactly the recorded findings and the same pass / fail outcome.
    """
    # When
    result = run_golden_case(case["sample"], case["settings"])

    # Then
    assert result["findings"] == case["expected"]["findings"]
    assert result["fails"] == case["expected"]["fails"]

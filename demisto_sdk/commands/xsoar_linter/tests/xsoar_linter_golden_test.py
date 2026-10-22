"""
Golden tests for the xsoar-linter rules.

test_files/golden/golden.json holds the results of the pylint-based xsoar-linter for every
(sample, settings) case, recorded by test_files/golden/record_golden.py.
Every engine must reproduce those results exactly: same findings (line, column, code, object, message)
and the same pass / fail outcome.

- engine "pylint": proves golden.json really reflects the current pylint implementation.
- engine "ast": proves the ast implementation matches it (skipped until the ast engine exists).
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest

GOLDEN_DIR = Path(__file__).parent / "test_files" / "golden"
GOLDEN_CASES: List[Dict[str, Any]] = json.loads(
    (GOLDEN_DIR / "golden.json").read_text()
)


def get_engine_runner(engine: str) -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
    if engine == "pylint":
        import sys

        sys.path.insert(0, str(GOLDEN_DIR))
        from record_golden import run_pylint_engine  # type: ignore[import-not-found]

        return run_pylint_engine

    runner = pytest.importorskip("demisto_sdk.commands.xsoar_linter.checkers.runner")
    return runner.run_golden_case


@pytest.mark.parametrize("engine", ["pylint", "ast"])
@pytest.mark.parametrize(
    "case", GOLDEN_CASES, ids=[case["id"] for case in GOLDEN_CASES]
)
def test_xsoar_linter_engine_matches_golden(engine: str, case: Dict[str, Any]):
    """
    Given:
        - A sample python file and the integration / script settings it is linted with
          (support level, script or integration, long running, python 2, yml commands).
        - The findings the pylint-based xsoar-linter reported for it, recorded in golden.json.
    When:
        - Running the given xsoar-linter engine on the sample with the same settings.
    Then:
        - The engine reports exactly the recorded findings and the same pass / fail outcome.
    """
    # Given
    run_engine = get_engine_runner(engine)

    # When
    result = run_engine(case["sample"], case["settings"])

    # Then
    assert result["findings"] == case["expected"]["findings"]
    assert result["fails"] == case["expected"]["fails"]

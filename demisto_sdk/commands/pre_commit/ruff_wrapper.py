import json
import os
import sys
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, NoReturn, Set, Tuple, Union

from git.repo import Repo
from unidiff import PatchSet

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.pre_commit.linter_parser import LinterViolation, RuffParser


def run(files: List[str], fail_autofixable: bool):
    ruff_command = f"ruff {','.join(files)} --format=json"  # TODO provide args
    logger.info(f"running {ruff_command}")

    try:
        process = os.popen(ruff_command)
        ruff_result_raw = process.read()
        ruff_exit_code = process.close()

        logger.debug(f"{ruff_result_raw=}")
        logger.debug(f"{ruff_exit_code=}")
    except Exception:
        logger.error("Failed running ruff")
        raise

    try:
        raw_violations = json.loads(ruff_result_raw)
    except json.JSONDecodeError:
        logger.error("failed parsing json from ruff output")
        raise

    all_violations = tuple(
        RuffParser.parse_single(raw_violation) for raw_violation in raw_violations
    )

    logger.debug(
        f"Parsed {len(all_violations)} Ruff violations:\n{_violations_to_string(all_violations)}"
    )

    logger.debug(f"{(changed_lines:=git_changed_lines())=}")

    if filtered_violations := filter_violations(
        all_violations, changed_lines, fail_autofixable
    ):
        exit_code(filtered_violations, fail_autofixable)
    logger.info("Done! No ruff violations were found.")


def exit_code(
    filtered_violations: Tuple[LinterViolation, ...], fail_autofixable: bool
) -> NoReturn:
    violation_count = len(filtered_violations)
    autofixable_count = sum(
        (bool(violation.is_autofixable) for violation in filtered_violations)
    )

    logger.info(f"Found {len(filtered_violations)} Ruff vioations")

    if (not fail_autofixable) and autofixable_count == violation_count:
        logger.info(
            "All violations found were autofixed - commit the changes and the step will pass"
        )
        sys.exit(0)

    logger.info(
        "\n".join(_violations_to_string(filtered_violations))
    )  # TODO Github Annotation forma
    sys.exit(1)


def filter_violations(
    violations: Iterable[LinterViolation],
    git_modified_lines: Dict[Path, Set[int]],
    fail_autofixable: bool,
    always_fail_on: Union[Set[str], FrozenSet] = frozenset(),
) -> Tuple[LinterViolation, ...]:
    """Filter out violations we don't want to show the user

    Args:
        violations (Iterable[LinterViolation]): Violations to filter.
        git_modified_lines (Dict[Path, Set[int]]): Map a path to its modified lines.
        fail_autofixable (bool): Whether to fail on autofixable violations
        always_fail_on (Set[str]): violation codes that should fail even if the line was not modified.

    Returns:
        Tuple[LinterViolation, ...]: Filtered violations.
    """

    return tuple(
        sorted(
            (
                violation
                for violation in violations
                if (
                    violation.row_start in git_modified_lines.get(violation.path, ())
                    or violation.error_code in always_fail_on
                )
                and not (fail_autofixable and violation.is_autofixable)
            ),
            key=lambda violation: str(
                (violation.path, violation.row_start, violation.error_code)
            ),
        )
    )


def git_changed_lines() -> Dict[Path, Set[int]]:
    """
    Returns:
        Dict[Path, Tuple[int]]: maps modified files, to the indices of the lines changed
    """
    repo = Repo("~/dev/demisto/demisto-sdk", search_parent_directories=True)  # TODO

    def parse_file_lines(patched_file: PatchSet) -> Set[int]:
        return {
            line.source_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_removed and line.value.strip()
        }

    return {
        Path(patch.file_path): parse_file_lines(patch)
        for patch in PatchSet(
            repo.git.diff(
                "HEAD",
                "origin/master",  # TODO
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
            )  # TODO diff order
        )
    }


def _violations_to_string(violations: Iterable[LinterViolation]) -> str:
    return "\n".join(str(e) for e in violations)

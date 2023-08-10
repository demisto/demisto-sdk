import json
import os
import sys
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Set, Tuple, Union

from git.repo import Repo
from unidiff import PatchSet

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.pre_commit.linter_parser import LinterViolation, RuffParser


def run(files: List[str], path: Path, print_github_action_annotation: bool):
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

    violations = tuple(
        RuffParser.parse_single(raw_violation) for raw_violation in raw_violations
    )
    logger.debug(f"Parsed {len(violations)} Ruff violations")

    logger.debug(f"{(changed_lines:=git_changed_lines(path))=}")

    if filtered_violations := filter_violations(violations, changed_lines):
        logger.info(f"Found {len(filtered_violations)}")
        for violation in filtered_violations:
            logger.error(violation)

            if print_github_action_annotation:
                print(  # noqa: T201 required for GitHub Annotations
                    violation.to_github_annotation()
                )
        sys.exit(1)

    logger.info("Done! No ruff violations were found.")


def filter_violations(
    violations: Iterable[LinterViolation],
    git_modified_lines: Dict[Path, Set[int]],
    always_fail_on: Union[Set[str], FrozenSet] = frozenset(),
) -> Tuple[LinterViolation, ...]:
    """Only return violations that started in one of the modified lines

    Args:
        violations (Iterable[LinterViolation]): Violations to filter.
        git_modified_lines (Dict[Path, Set[int]]): Map a path to its modified lines.
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
            ),
            key=lambda violation: str(
                (violation.path, violation.row_start, violation.error_code)
            ),
        )
    )


def git_changed_lines(
    path: Path, base_branch: str = "origin/master"
) -> Dict[Path, Set[int]]:
    """
    Returns:
        Dict[Path, Tuple[int]]: maps modified files, to the indices of the lines changed
    """

    def parse_modified_lines(patched_file: PatchSet) -> Set[int]:
        return {
            line.source_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_removed and line.value.strip()
        }

    repo = Repo(path, search_parent_directories=True)

    return {
        Path(patch.file_path): parse_modified_lines(patch)
        for patch in PatchSet(
            repo.git.diff(
                "HEAD",
                base_branch,
                ignore_blank_lines=True,
                ignore_space_at_eol=True,
            )  # TODO diff order
        )
    }

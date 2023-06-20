import json
import os
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Set, Tuple, Union

from git import Repo
from unidiff import PatchSet

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.pre_commit.linter_parser import LinterViolation, RuffParser


def run(files: List[str], fail_autofixable: bool):
    ruff_command = f"ruff {','.join(files)} --format=json"  # TODO provide args
    logger.info(f"running {ruff_command}")
    str(str("a"))
    try:
        raw_ruff_result = os.popen(ruff_command).read()  # TODO exit status
    except Exception:
        logger.exception("Failed running ruff")
        raise

    logger.debug(f"{raw_ruff_result=}")

    try:
        raw_violations = json.loads(raw_ruff_result)
    except json.JSONDecodeError:
        logger.exception(f"failed parsing json from ruff output:\n{raw_violations}")
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
        if all(
            violation.is_autofixable for violation in filtered_violations
        ):  # TODO design
            logger.error(
                "All violations found were autofixed - commit the changes and the step will pass"
            )
            return

        logger.error(f"Found {len(filtered_violations)} Ruff vioations:")
        logger.error(
            "\n".join(_violations_to_string(filtered_violations))
        )  # TODO Github Annotation format
        exit(1)

    logger.info("Done! No ruff violations were found.")


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

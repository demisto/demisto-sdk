import json
import os
from pathlib import Path
from typing import Dict, Iterable, List, Set

from git import Repo
from unidiff import PatchSet

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.pre_commit.linter_parser import LinterError, RuffParser


def run(files: List[str]):
    files_string = ",".join(files)
    raw_ruff_result = os.popen(f"ruff {files_string} --format=json").read()
    logger.debug(f"{raw_ruff_result=}")

    try:
        raw_errors_json = json.loads(raw_ruff_result)
    except json.JSONDecodeError:
        logger.exception(f"failed parsing\n{raw_errors_json}")

    errors = tuple(RuffParser.parse_single(raw_error) for raw_error in raw_errors_json)

    error_string = "\n".join(str(e) for e in errors)
    logger.debug(f"Parsed {len(errors)} errors:\n{error_string}")

    changed_lines = get_changed_lines()
    logger.debug(f"{changed_lines=}")

    filter_errors(errors, changed_lines)
    raise NotImplementedError  # TODO


def filter_errors(errors: Iterable[LinterError], modified_lines: Dict[Path, Set[int]]):
    """Only keeps errors that happened in a modified line"""
    return tuple(
        error
        for error in errors
        if error.row_start in modified_lines.get(error.path, ())
    )


def get_changed_lines() -> Dict[Path, Set[int]]:
    """
    Returns:
        Dict[Path, Tuple[int]]: maps every modified file, to the indices of the lines changed in it
    """
    repo = Repo("~/dev/demisto/demisto-sdk")  # TODO

    uni_diff_text = repo.git.diff(
        "HEAD", "origin/master", ignore_blank_lines=True, ignore_space_at_eol=True
    )  # TODO diff order

    def parse_changed_lines(patched_file: PatchSet) -> Set[int]:
        return {
            line.source_line_no
            for hunk in patched_file
            for line in hunk
            if line.is_removed and line.value.strip()
        }

    return {
        Path(patch.file_path): parse_changed_lines(patch)
        for patch in PatchSet(uni_diff_text)
    }

import os
import re
from pathlib import Path
from typing import Dict, Optional, Set, Tuple
from itertools import chain

from parse_linter import LinterError

ROW_DIFF_REGEX = re.compile(r"\+\+\+ ./(.*?)\n@@ -\d,\d \+(\d,\d+) @@")
SINGLE_LINE_REGEX = re.compile(r"\d+")
MULTI_LINE_REGEX = re.compile(r"(?P<start>\d+),(?P<end>\d+)")


def _parse_changed_files(raw_diff: list) -> Dict[Path, Set[int]]:
    result: Dict[Path, Set[int]] = {}

    current_path: Optional[Path] = None
    current_changed_lines: Set[int] = set()

    for row_ix, row in enumerate(raw_diff):
        if SINGLE_LINE_REGEX.fullmatch(row):
            current_changed_lines.update({int(row)})
        elif match := MULTI_LINE_REGEX.fullmatch(row):
            current_changed_lines.update(
                range(int(match.group(1)), int(match.group(2)) + 1)
            )
        else:
            new_path = Path(row)
            if not new_path.exists():  # unexpected value
                raise RuntimeError(
                    f"cannot parse diff lines from row, and it doesn't exist as a path: {new_path}"
                )
            if current_path:  # append temp to result and restart parsing lines
                result[current_path] = current_changed_lines

                current_path = new_path
                current_changed_lines = set()
            else:
                current_path = new_path

        if row_ix == len(raw_diff) - 1:  # last line
            if not current_path:
                raise RuntimeError(
                    "Reached end of a non-blank diff file without parsing anything"
                )
            result[current_path] = current_changed_lines

    return result


def get_diff() -> Dict[Path, Set[int]]:
    raw: str = os.popen(
        r"git diff master...HEAD --unified=0"
    ).read()
    raw_diff = list(chain.from_iterable(ROW_DIFF_REGEX.findall(raw, re.IGNORECASE | re.MULTILINE)))
    return _parse_changed_files(raw_diff)

def filter_errors(errors: Tuple[LinterError, ...]):
    # return errors that occur in lines showing in the diff
    diff = get_diff()
    return tuple(
        filter(lambda error: error.row_start in diff.get(error.path, ()), errors),
    )

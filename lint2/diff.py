from pathlib import Path
import os
from typing import Optional, Dict, Set


def _parse_changed_files(raw_diff: str) -> Dict[str, Set[int]]:
    result: Dict[str, Set[int]] = {}

    current_file_name: Optional[str] = None
    current_changed_lines: Set[int] = set()

    for row in raw_diff.splitlines():
        if Path(row).exists():  # reached a file name line
            if current_file_name:  # append temp to result and restart
                result[current_file_name] = current_changed_lines

            current_file_name = row
            current_changed_lines = set()

        else:  # row marks a line change
            try:
                parts = tuple(map(int, row.split(",")))
            except TypeError:
                raise TypeError(f"could not parse numbers from {row=}")

            if (part_count := len(parts)) == 2:  # multi-line change, e.g. 1,4
                current_changed_lines.update(range(parts[0], parts[1] + 1))
            elif part_count == 1:  # single-line change
                current_changed_lines.add(parts[0])  # add the changed line
            else:
                raise ValueError(f"unexpected format: {row}")

    if current_file_name and (
        (not result) or (current_file_name in result)
    ):  # last line
        result[current_file_name] = current_changed_lines

    return result


def get_diff() -> Dict[str, Set[int]]:
    raw = os.popen(
        "git diff master...HEAD --unified=0 | grep -Po '^\+\+\+ ./\K.*|^@@ -[0-9]+(,[0-9]+)? \+\K[0-9]+(,[0-9]+)?(?= @@)'"
    )
    return _parse_changed_files(raw)

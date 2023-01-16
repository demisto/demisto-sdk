from pathlib import Path
import os
from typing import NamedTuple
from typing import Optional


class ChangedFile(NamedTuple):
    file_name: str
    change_ranges: tuple[range, ...]


def _parse_changed_files(raw_diff: str) -> tuple[ChangedFile, ...]:
    changed_files: list[ChangedFile] = []

    current_file_name: Optional[str] = None
    current_ranges: list[range] = []

    for row in raw_diff.splitlines():
        if Path(row).exists():  # resets the current result
            if current_file_name:
                changed_files.append(
                    ChangedFile(current_file_name, tuple(current_ranges))
                )

            current_file_name = row
            current_ranges = []

        else:  # row marks a line change
            try:
                parts = tuple(map(int, row.split(",")))
            except TypeError:
                raise TypeError(f"could not parse numbers from {row=}")

            if (part_count := len(parts)) == 2:  # multi-line change
                current_ranges.append(range(parts[0], parts[1] + 1))
            elif part_count == 1:  # single-line change
                current_ranges.append(range(parts[0], parts[0] + 1))
            else:
                raise ValueError(f"unexpected format: {row}")

    if current_file_name and (
        not changed_files or changed_files[-1].file_name != current_file_name
    ):  # last line
        changed_files.append(ChangedFile(current_file_name, tuple(current_ranges)))

    return tuple(changed_files)


def filter_error(row: int, change_ranges: tuple[range, ...]):
    return any(row in _range for _range in change_ranges)


def get_diff() -> tuple[ChangedFile, ...]:
    raw = os.popen(
        "git diff master...HEAD --unified=0 | grep -Po '^\+\+\+ ./\K.*|^@@ -[0-9]+(,[0-9]+)? \+\K[0-9]+(,[0-9]+)?(?= @@)'"
    )
    return _parse_changed_files(raw)

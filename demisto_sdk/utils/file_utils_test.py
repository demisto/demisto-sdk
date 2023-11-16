from pathlib import Path
from typing import Tuple

from pytest import TempPathFactory, fixture

from demisto_sdk.utils.file_utils import (
    TOKEN_ADDED,
    TOKEN_BOTH,
    TOKEN_NOT_PRESENT,
    TOKEN_REMOVED,
    get_file_diff,
    merge_files,
)


class TestFileDiff:

    @fixture(autouse=True)
    def _get_tmp_diff_files(self, tmp_path: TempPathFactory):
        self.original = (Path(str(tmp_path)) / "original")
        self.modified = (Path(str(tmp_path)) / "modified")

        self.original.touch()
        self.modified.touch()

    def test_get_file_diff_rm_add(self):

        """
        Çreate file diff with 2 2-line text files with one character removed 
        from the first line and appended to the second line.

        Given:
        - An original file with the following contents:

        ```
        abcd
        efghi
        ```

        - A modified file with the following contents:

        ```
        acd
        befghi
        ```

        When:
        - Calculating the file difference.

        Then:
        - There are 6 lines in the diff (2 removal, 2 added, 2 change indicator lines)
        """


        expected_diff = [
            f"{TOKEN_REMOVED}abcd\n",
            f"{TOKEN_NOT_PRESENT} -\n",
            f"{TOKEN_ADDED}acd\n",
            f"{TOKEN_REMOVED}efghi\n",
            f"{TOKEN_ADDED}befghi\n",
            f"{TOKEN_NOT_PRESENT}+\n",
        ]

        rm_index = 1

        line_1_original = 'abcd'
        line_2_original = 'efghi'

        original_lines = [line_1_original, line_2_original]

        line_1_modified = line_1_original[:rm_index] + line_1_original[rm_index + 1:]
        line_2_modified = line_1_original[rm_index] + line_2_original
        modified_lines = [line_1_modified, line_2_modified]

        with self.original.open("w") as f:
            f.writelines(line + '\n' for line in original_lines)

        with self.modified.open("w") as f:
            f.writelines(line + '\n' for line in modified_lines)

        actual_diff = get_file_diff(self.original, self.modified)
        assert len(expected_diff) == 6
        assert expected_diff == actual_diff

    def test_get_file_diff_add_new_section(self):

        original_lines = [
            "# Title\n",
            "## Section 1\n",
            "## Section 2\n"
        ]

        modified_lines = [
            "# Title\n",
            "## Section 1\n",
            "## Section 2\n",
            "## Section 3\n",
        ]

        expected = [
            f"{TOKEN_BOTH} {modified_lines[0]}",
            f"{TOKEN_BOTH} {modified_lines[1]}",
            f"{TOKEN_BOTH} {modified_lines[2]}",
            f"{TOKEN_ADDED}{modified_lines[3]}"
        ]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(original_lines)
            m.writelines(modified_lines)


        actual = get_file_diff(self.original, self.modified)

        assert actual == expected

        assert True

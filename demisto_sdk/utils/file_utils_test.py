from pathlib import Path

from pytest import TempPathFactory

from demisto_sdk.utils.file_utils import (
    TOKEN_ADDED,
    TOKEN_BOTH,
    TOKEN_NOT_PRESENT,
    TOKEN_REMOVED,
    get_file_diff,
    merge_files,
)


def test_get_file_diff_2_line_rm_add(tmp_path: TempPathFactory):

    """
    Test a 2-line text file with one character removed from the 
    first line and appended to the second line.

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


    original = (Path(str(tmp_path)) / "original")
    modified = (Path(str(tmp_path)) / "modified")
    
    original.touch()
    modified.touch()

    rm_index = 1

    line_1_original = 'abcd'
    line_2_original = 'efghi'

    original_lines = [line_1_original, line_2_original]

    line_1_modified = line_1_original[:rm_index] + line_1_original[rm_index + 1:]
    line_2_modified = line_1_original[rm_index] + line_2_original
    modified_lines = [line_1_modified, line_2_modified]

    with original.open("w") as f:
        f.writelines(line + '\n' for line in original_lines)

    with modified.open("w") as f:
        f.writelines(line + '\n' for line in modified_lines)

    actual_diff = get_file_diff(original, modified)
    assert expected_diff == actual_diff

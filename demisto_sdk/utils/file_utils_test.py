import os
from pathlib import Path

from pytest import TempPathFactory, fixture, raises
from pytest_mock import MockerFixture

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.utils.file_utils import (
    TOKEN_ADDED,
    TOKEN_BOTH,
    TOKEN_NOT_PRESENT,
    TOKEN_REMOVED,
    get_file_diff,
    merge_files,
)

DEMISTO_SDK_PATH = os.path.join(git_path(), "demisto_sdk")
TEST_FILES = os.path.join(DEMISTO_SDK_PATH, "utils", "test_files")


class TestFileUtils:
    @fixture(autouse=True)
    def _get_tmp_diff_files(self, tmp_path: TempPathFactory):
        self.original = Path(str(tmp_path)) / "original"
        self.modified = Path(str(tmp_path)) / "modified"

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

        line_1_original = "abcd"
        line_2_original = "efghi"

        original_lines = [line_1_original, line_2_original]

        line_1_modified = line_1_original[:rm_index] + line_1_original[rm_index + 1 :]
        line_2_modified = line_1_original[rm_index] + line_2_original
        modified_lines = [line_1_modified, line_2_modified]

        with self.original.open("w") as f:
            f.writelines(line + "\n" for line in original_lines)

        with self.modified.open("w") as f:
            f.writelines(line + "\n" for line in modified_lines)

        actual_diff = get_file_diff(self.original, self.modified)
        assert len(expected_diff) == 6
        assert expected_diff == actual_diff

    def test_get_file_diff_add_new_section(self):
        """
        Çreate file diff with 2 2-line text files with one character removed
        from the first line and appended to the second line.

        Given:
        - An original file with the following contents:

        ```
        # Title
        ## Section 1
        ## Section 2
        ```

        - A modified file with the following contents:

        ```
        # Title
        ## Section 1
        ## Section 2
        ## Section 3
        ```

        When:
        - Calculating the file difference.

        Then:
        - There are 4 lines in the diff (3 same line, 1 added)
        """

        original_lines = ["# Title\n", "## Section 1\n", "## Section 2\n"]

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
            f"{TOKEN_ADDED}{modified_lines[3]}",
        ]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(original_lines)
            m.writelines(modified_lines)

        actual = get_file_diff(self.original, self.modified)

        assert actual == expected

        assert True

    def test_merge_files_replaced_section(self, tmp_path: TempPathFactory):
        """
        Take 2 files and merge them to check if the output file is
        as expected.

        Given:
        - An original file with the following contents:

        ```
        # Title

        # Section 1
        ```

        - A modified file with the following contents:

        ```
        # Title

        # Section 2
        ```

        When:
        - Merging 2 files with a removed and an added section

        Then:
        - The merged file should be:

        ```
        # Title

        # Section 2
        ```
        """

        original_lines = ["# Title\n\n", "## Section 1\n"]

        modified_lines = [original_lines[0], original_lines[1].replace("1", "2")]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(original_lines)
            m.writelines(modified_lines)

        actual: Path = merge_files(self.original, self.modified, tmp_path.__str__())

        assert actual.exists()
        assert actual.name == f"{self.original.name}-merged"
        assert actual.read_text() == "# Title\n\n## Section 2\n"

    def test_merge_files_new_section(self, tmp_path: TempPathFactory):
        """
        Take 2 files and merge them to check if the output file is
        as expected.

        Given:
        - An original file with the following contents:

        ```
        # Title

        # Section 1
        ```

        - A modified file with the following contents:

        ```
        # Title

        # Section 2
        ```

        When:
        - Merging 2 files with a removed and an added section

        Then:
        - The merged file should be:

        ```
        # Title

        # Section 1

        # Section 2
        ```
        """

        original_lines = ["# Title\n\n", "## Section 1\n"]

        modified_lines = [
            original_lines[0],
            original_lines[1],
            original_lines[1].replace("1", "2"),
        ]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(original_lines)
            m.writelines(modified_lines)

        actual = merge_files(self.original, self.modified, tmp_path.__str__())

        if actual:
            assert actual.exists()
            assert actual.name == f"{self.original.name}-merged"
            assert actual.read_text() == "# Title\n\n## Section 1\n## Section 2\n"

    def test_merge_files_readmes(self, tmp_path: TempPathFactory):
        """
        Take 2 README files and merge them to check if the output file is
        as expected.

        Given:
        - An original README file with 2 commands and their respective
        Command example, Command Context, Human Readable Output sections
        - A generated README file with 3 commands
        and removed Command example, Command Context, Human Readable Output sections.

        When:
        - Merging both files.

        Then:
        - The merged file will include 3 commands and the respective
        Command example, Command Context, Human Readable Output sections
        """

        original = Path(os.path.join(TEST_FILES, "simple_original.md"))
        generated = Path(os.path.join(TEST_FILES, "simple_generated.md"))

        output = merge_files(original, generated, tmp_path.__str__())

        if output:
            assert "helloworld-say-hello" in output.read_text()
            assert "helloworld-alert-list" in output.read_text()
            assert "helloworld-alert-note-create" in output.read_text()

            assert output.read_text().count("Base Command") == 3
            assert output.read_text().count("Input") == 3
            assert output.read_text().count("Command example") == 3
            assert output.read_text().count("Context Example") == 3
            assert output.read_text().count("Human Readable Output") == 3

    def test_merge_files_identical(self, tmp_path: TempPathFactory):
        """
        Check that the original file is returned when the files are identical.

        Given:
        - An original file with the following contents:

        ```
        # Title

        # Section 1
        ```

        - A modified file with the following contents:

        ```
        # Title

        # Section 1
        ```

        When:
        - Merging 2 files.

        Then:
        - The merged file should be the original file.
        ```
        """

        lines = ["# Title\n\n", "## Section 1\n"]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(lines)
            m.writelines(lines)

        actual = merge_files(self.original, self.modified, tmp_path.__str__())
        expected = self.original

        assert actual == expected

    def test_merge_files_f1_dne(self, tmp_path: TempPathFactory):
        """
        Test to ensure that when the original file doesn't exist, the modified one is returned.

        Given:
        - 2 files, original and modified.

        When:
        - The original file doesn't exist.

        Then:
        - The modified file is returned.
        """

        lines = ["# Title\n\n", "## Section 1\n"]

        # Remove the original file
        self.original.unlink()

        with self.modified.open("w") as m:
            m.writelines(lines)

        expected = self.modified
        actual = merge_files(self.original, self.modified, tmp_path.__str__())

        assert actual == expected

    def test_merge_files_f2_dne(self, tmp_path: TempPathFactory):
        """
        Test to ensure that when the modified file doesn't exist, the original one is returned.

        Given:
        - 2 files, original and modified.

        When:
        - The modified file doesn't exist.

        Then:
        - The original file is returned.
        """

        lines = ["# Title\n\n", "## Section 1\n"]

        # Remove the modified file
        self.modified.unlink()

        with self.original.open("w") as o:
            o.writelines(lines)

        expected = self.original
        actual = merge_files(self.original, self.modified, tmp_path.__str__())

        assert actual == expected

    def test_merge_files_f1_f2_dne(self, tmp_path: TempPathFactory):
        """
        Test when neither the original or modifed files exist we return `None`.

        Given:
        - 2 files, original and modified.

        When:
        - The modified file doesn't exist.
        - The original file doesn't exist.

        Then:
        - None is returned.
        """

        # Remove both files
        self.original.unlink()
        self.modified.unlink()

        actual = merge_files(self.original, self.modified, tmp_path.__str__())

        assert not actual

    def test_merge_files_f1_unreadable(self, tmp_path: TempPathFactory):
        """
        Test when the original file is unreadable.

        Given:
        - 2 files, original and modified.

        When:
        - The modified file is unreadable.

        Then:
        - The modified file will be returned.
        """

        original_lines = ["# Title\n\n", "## Section 1\n"]

        modified_lines = [original_lines[0], original_lines[1].replace("1", "2")]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(original_lines)
            m.writelines(modified_lines)

        # Set original file as write only
        os.chmod(self.original.__str__(), os.O_WRONLY)

        output = merge_files(self.original, self.modified, tmp_path.__str__())

        assert output == self.modified

    def test_merge_files_exception_process(self, tmp_path: TempPathFactory):
        """
        Test when there's an exception while processing the merge.

        Given:
        - 2 files, original and modified.

        When:
        - The processing throws an `Exception`.

        Then:
        - The modified file will be returned.
        """

        original_lines = ["# Title\n\n", "## Section 1\n"]

        modified_lines = [original_lines[0], original_lines[1].replace("1", "2")]

        with self.original.open("w") as o, self.modified.open("w") as m:
            o.writelines(original_lines)
            m.writelines(modified_lines)

        with raises(Exception):
            output = merge_files(self.original, self.modified, tmp_path.__str__())
            assert output == self.modified

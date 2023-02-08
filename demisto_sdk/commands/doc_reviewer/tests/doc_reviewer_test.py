import os
import re
from enum import Enum
from os import path
from pathlib import Path
from typing import List

import pytest
from click.testing import CliRunner, Result

from demisto_sdk import __main__
from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.tools import (
    find_type,
    get_yaml,
    is_xsoar_supported_pack,
)
from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
from demisto_sdk.tests.integration_tests.validate_integration_test import (
    AZURE_FEED_PACK_PATH,
)
from TestSuite.json_based import JSONBased
from TestSuite.pack import Pack
from TestSuite.test_tools import ChangeCWD


class TestDocReviewFilesAreFound:
    """
    Tests scenarios in which files are found before performing doc-review.
    """

    def test_find_files_from_invalid_path(self):
        """
        Given -
            invalid path file.

        When -
            trying to find files to do doc-reviews on.

        Then -
            Ensure no files are found.
        """
        doc_review = DocReviewer(file_paths=["test"])
        assert doc_review.run_doc_review()
        assert not doc_review.files

    def test_find_files_from_dir(self, valid_spelled_content_pack):
        """
        Given -
            valid pack directory path.

        When -
            trying to find files to do doc-reviews on.

        Then -
            Ensure the files that are found exist in the directory.
        """
        # must set file path here it otherwise use_git=True
        doc_review = DocReviewer(file_paths=[valid_spelled_content_pack.path])
        doc_review.get_files_to_run_on(file_path=valid_spelled_content_pack.path)
        for file in doc_review.files:
            assert path.exists(file)

    def test_find_single_file(self, valid_spelled_content_pack):
        """
        Given -
            valid integration yml file path.

        When -
            trying to find the file to do the doc-review on.

        Then -
            Ensure the file that was found exist in the directory.
        """
        doc_review = DocReviewer(
            file_paths=[valid_spelled_content_pack.integrations[0].yml.path]
        )
        doc_review.get_files_to_run_on(
            file_path=valid_spelled_content_pack.integrations[0].yml.path
        )
        for file in doc_review.files:
            assert path.exists(file)

    def test_find_files_from_git(self, mocker, valid_spelled_content_pack):
        """
        Given -
            valid pack directory path.

        When -
            trying to find files to do doc-reviews on from git.

        Then -
            Ensure the files that git reports are the same found that are meant to be doc-reviewed.
        """
        changed_files_mock = [
            valid_spelled_content_pack.integrations[0].yml.path,
            valid_spelled_content_pack.scripts[0].yml.path,
        ] + [rn.path for rn in valid_spelled_content_pack.release_notes]

        mocker.patch.object(
            DocReviewer, "gather_all_changed_files", return_value=changed_files_mock
        )
        doc_review = DocReviewer(use_git=True)
        doc_review.get_files_to_run_on(file_path="")
        assert set(doc_review.files) == set(changed_files_mock)

    def test_find_only_supported_files(self, valid_spelled_content_pack):
        """
        Given -
            valid pack directory path.

        When -
            trying to find files from a directory.

        Then -
            Ensure the files that are found are only supported files.
        """
        doc_review = DocReviewer(file_paths=[valid_spelled_content_pack.path])
        doc_review.get_files_to_run_on(file_path=valid_spelled_content_pack.path)
        for file in doc_review.files:
            assert find_type(path=file) in doc_review.SUPPORTED_FILE_TYPES


class TestDocReviewOnReleaseNotesOnly:
    """
    Tests scenarios which are related to executing doc-review with --release-notes
    """

    def test_doc_review_with_release_notes_is_skipped_on_invalid_yml_file(
        self, malformed_integration_yml
    ):
        """
        Given -
            malformed yml integration file.

        When -
            Calling doc-review with --release-notes.

        Then -
            Ensure that no exception/error is raised and that the malformed files were not added to the files to review.
        """
        _path = malformed_integration_yml.path

        try:
            doc_reviewer = DocReviewer(file_paths=[_path], release_notes_only=True)
            assert doc_reviewer.run_doc_review()
            assert not doc_reviewer.files
        except ValueError as err:
            assert False, str(err)

    def test_doc_review_with_release_notes_is_skipped_on_invalid_json_file(
        self, malformed_incident_field: JSONBased
    ):
        """
        Given -
            malformed json incident field.

        When -
            Calling doc-review with --release-notes.

        Then -
            Ensure that no exception/error is raised and that the malformed files were not added to the files to review.
        """
        _path = malformed_incident_field.path

        try:
            doc_reviewer = DocReviewer(file_paths=[_path], release_notes_only=True)
            assert doc_reviewer.run_doc_review()
            assert not doc_reviewer.files
        except ValueError as err:
            assert False, str(err)

    def test_doc_review_is_performed_only_on_release_notes(
        self, valid_spelled_content_pack
    ):
        """
        Given
            - a pack

        When
            - Running doc-review with release-notes only.

        Then
            - Ensure The files that were doc-reviewed are only release-notes.
        """
        doc_reviewer = DocReviewer(
            file_paths=[valid_spelled_content_pack.path], release_notes_only=True
        )
        assert doc_reviewer.run_doc_review()
        assert set(doc_reviewer.files) == {
            rn.path for rn in valid_spelled_content_pack.release_notes
        }

    def test_get_invalid_files_from_git_with_release_notes(
        self, mocker, malformed_integration_yml, malformed_incident_field
    ):
        """
        Given -
            malformed json/yml.

        When -
            Collecting files from git and release-notes is set to True.

        Then -
            Ensure that no exception/error is raised and that the malformed files were not added to the files for review.
        """
        mocker.patch.object(
            DocReviewer,
            "gather_all_changed_files",
            return_value=[
                malformed_integration_yml.path,
                malformed_incident_field.path,
            ],
        )
        try:
            doc_reviewer = DocReviewer(release_notes_only=True)
            doc_reviewer.get_files_from_git()
            assert not doc_reviewer.files
        except ValueError as err:
            assert False, str(err)

    def test_supported_files_are_only_release_notes(self):
        """
        Given -
            doc-reviewer with release-notes only.

        When -
            initializing doc-reviewer.

        Then -
            Ensure supported files contain only release-notes.
        """
        assert DocReviewer(release_notes_only=True).SUPPORTED_FILE_TYPES == [
            FileType.RELEASE_NOTES
        ]


class TestDocReviewPack:
    """
    Test scenarios in which the doc review is performed on new pack.
    """

    def test_invalid_misspelled_files_are_correct(self, invalid_spelled_content_pack):
        """
        Given -
            Pack files with invalid content spelling.

        When -
            Running doc-review on misspelled files.

        Then -
            Ensure doc-review fails and all the misspelled files are found.
        """
        pack, misspelled_files = invalid_spelled_content_pack

        doc_reviewer = DocReviewer(file_paths=[pack.path])
        assert not doc_reviewer.run_doc_review()
        assert doc_reviewer.found_misspelled
        assert len(doc_reviewer.files_with_misspells) == len(misspelled_files)
        assert doc_reviewer.files_with_misspells == misspelled_files

    def test_invalid_misspelled_files_with_no_failure(
        self, invalid_spelled_content_pack
    ):
        """
        Given -
            Pack files with invalid content spelling and 'no_failure' input parameter set to True.

        When -
            Running doc-review on misspelled files.

        Then -
            Ensure doc-review still succeeds.
        """
        pack, _ = invalid_spelled_content_pack

        doc_reviewer = DocReviewer(file_paths=[pack.path], no_failure=True)
        assert doc_reviewer.run_doc_review()

    def test_valid_spelled_files(self, valid_spelled_content_pack):
        """
        Given -
            Pack files with valid content spelling.

        When -
            Running doc-review on correctly spelled files.

        Then -
            Ensure doc-review succeed and there aren't any misspelled files found.
        """
        pack = valid_spelled_content_pack

        doc_reviewer = DocReviewer(file_paths=[pack.path])
        assert doc_reviewer.run_doc_review()
        assert not doc_reviewer.found_misspelled
        assert len(doc_reviewer.files_with_misspells) == 0
        assert doc_reviewer.files_with_misspells == set()

    def test_failure_on_malformed_rns(self, pack):
        """
        Given -
            Pack files with malformed release notes but correct spelling.

        When -
            Running doc-review.

        Then -
            Ensure malformed release notes are found.
            Ensure no misspelled words were found.
            Ensure doc-review returned False to indicate failure.
        """
        rn = pack.create_release_notes(
            version="release-note-0",
            content="\n#### Script\n##### Script Name\n- blah blah",
        )
        doc_reviewer = DocReviewer(file_paths=[pack.path])
        result = doc_reviewer.run_doc_review()
        assert rn.path in doc_reviewer.malformed_rn_files
        assert not doc_reviewer.found_misspelled
        assert not result


class TestDocReviewXSOAROnly:

    """
    Tests for the `--xsoar-only` flag.
    """

    default_args = ["--xsoar-only"]

    class CommandResultCode(Enum):

        """
        Holds result code for the execution of `doc-review` command.
        """

        SUCCESS = 0
        FAIL = 1

    def run_doc_review_cmd(self, cmd_args: List[str]) -> Result:

        """
        Uses the Click CLI runner to invoke a command with input arguments and returns the result
        """

        args: List[str] = self.default_args + cmd_args

        return CliRunner().invoke(__main__.doc_review, args)

    def test_valid_supported_pack(self, supported_pack: Pack):

        """
        Given -
            An XSOAR-supported Pack with correct spelling.

        When -
            Running `doc-review` on XSOAR-supported Pack with `--xsoar-only` flag set.

        Then -
            Ensure `doc-review` succeeds.
        """

        cmd_args: List[str] = [
            "--input",
            supported_pack.path,
        ]

        result = self.run_doc_review_cmd(cmd_args)

        assert result.exit_code == self.CommandResultCode.SUCCESS.value

    def test_valid_non_supported_pack(self, non_supported_pack: Pack):

        """
        Given -
            A non-XSOAR-supported Pack with correct spelling.

        When -
            Running `doc-review` on a non-XSOAR-supported Pack with `--xsoar-only` flag set.

        Then -
            Ensure `doc-review` succeeds.
        """

        cmd_args: List[str] = [
            "--input",
            non_supported_pack.path,
        ]

        result = self.run_doc_review_cmd(cmd_args)

        assert result.exit_code == self.CommandResultCode.SUCCESS.value

    def test_valid_multiple_supported_packs(self, supported_packs: List[Pack]):

        """
        Given -
            2 XSOAR-supported Packs with correct spelling.

        When -
            Running `doc-review` on XSOAR-supported Pack with `--xsoar-only` flag set.

        Then -
            Ensure `doc-review` succeeds.
        """

        cmd_args: List[str] = ["--xsoar-only"]
        for pack in supported_packs:
            cmd_args.append("--input")
            cmd_args.append(pack.path)

        result = self.run_doc_review_cmd(cmd_args)

        assert result.exit_code == self.CommandResultCode.SUCCESS.value

    def test_invalid_non_supported_pack(self, non_supported_pack_mispelled: Pack):

        """
        Given -
            A non-XSOAR-supported Pack with incorrect spelling.

        When -
            Running `doc-review` on a non-XSOAR-supported Pack with `--xsoar-only` flag set.

        Then -
            Ensure `doc-review` succeeds.
        """

        cmd_args: List[str] = [
            "--input",
            non_supported_pack_mispelled.path,
        ]

        result = self.run_doc_review_cmd(cmd_args)

        assert result.exit_code == self.CommandResultCode.SUCCESS.value

    def test_invalid_supported_pack(self, supported_pack_mispelled: Pack):

        """
        Given -
            A XSOAR-supported Pack with incorrect spelling.

        When -
            Running `doc-review` on a non-XSOAR-supported Pack with `--xsoar-only` flag set.

        Then -
            Ensure `doc-review` succeeds.
        """

        cmd_args: List[str] = [
            "--input",
            supported_pack_mispelled.path,
        ]

        result = self.run_doc_review_cmd(cmd_args)

        assert result.exit_code == self.CommandResultCode.FAIL.value

    def test_invalid_mix_packs(self, mix_invalid_packs: List[Pack]):

        """
        Given -
            2 Packs, one community, one XSOAR-supported with incorrect spelling.

        When -
            Running `doc-review` on both Packs with `--xsoar-only` flag set.

        Then -
            Ensure `doc-review` fails.
        """

        cmd_args: List[str] = ["--xsoar-only"]
        for pack in mix_invalid_packs:
            cmd_args.append("--input")
            cmd_args.append(pack.path)

        result = self.run_doc_review_cmd(cmd_args)

        assert result.exit_code == self.CommandResultCode.FAIL.value


@pytest.mark.usefixtures("are_mock_calls_supported_in_python_version")
class TestDocReviewPrinting:
    """
    Test scenarios of doc-review printing.
    """

    MOCKED_FILES = ["file1", "file2"]
    GREEN_FG = {"fg": "green"}
    BRIGHT_RED_FG = {"fg": "bright_red"}
    README_SKIPPED_REGEX = r"^File '.*/README.md' was skipped because it does not belong to an XSOAR-supported Pack"
    RN_SKIPPED_REGEX = r"^File '.*/ReleaseNotes/.*.md' was skipped because it does not belong to an XSOAR-supported Pack"
    FILE_MISSPELL_FOUND_REGEX = r"Words that might be misspelled were found in .*:"

    class SpelledFileType:
        """
        INVALID = invalid spelled files.
        VALID - valid spelled files.
        BOTH_INVALID_AND_VALID - both invalid spelled files and valid spelled files are required.
        INVALID_RELEASE_NOTES - invalid release-notes files.
        """

        INVALID = "invalid"
        VALID = "valid"
        BOTH_INVALID_AND_VALID = "invalid_and_valid"
        INVALID_RELEASE_NOTES = "invalid_release_notes"

    def get_file_report_mocker(self, mocker, files_type):
        """
        Returns a mock of the file report.

        Args:
            mocker (MockerFixture): a mocker object.
            files_type (str): whether mock misspelled files or valid spelled files or both are required.


        Returns:
            MagicMock: a magic mock object of the click 'secho' function.
        """
        import click

        doc_reviewer = DocReviewer()

        if files_type == self.SpelledFileType.VALID:
            doc_reviewer.files_without_misspells = self.MOCKED_FILES
        elif files_type == self.SpelledFileType.INVALID:
            doc_reviewer.files_with_misspells = self.MOCKED_FILES
        elif files_type == self.SpelledFileType.INVALID_RELEASE_NOTES:
            doc_reviewer.malformed_rn_files = self.MOCKED_FILES
        else:
            doc_reviewer.files_with_misspells = self.MOCKED_FILES
            doc_reviewer.files_without_misspells = self.MOCKED_FILES

        secho_mocker = mocker.patch.object(click, "secho")
        doc_reviewer.print_file_report()

        return secho_mocker

    def test_printing_of_valid_spelled_files(self, mocker):
        """
        Given -
            Files reported as valid spelled files.

        When -
            Printing files report.

        Then -
            Ensure only the files without misspells are printed.
        """
        secho_mocker = self.get_file_report_mocker(
            mocker=mocker, files_type=self.SpelledFileType.VALID
        )

        first_call = secho_mocker.mock_calls[0]
        assert "Files Without Misspells" in first_call.args[0]
        assert first_call.kwargs == self.GREEN_FG

        second_call = secho_mocker.mock_calls[1]
        assert "file1\nfile2" in second_call.args[0]
        assert second_call.kwargs == self.GREEN_FG

        for i in range(2, len(secho_mocker.mock_calls)):
            assert "Files With Misspells" not in secho_mocker.mock_calls[i].args

    def test_printing_invalid_spelled_files(self, mocker):
        """
        Given -
            Files reported as invalid spelled files.

        When -
            Printing files report.

        Then -
            Ensure only the files with misspells are printed.
        """
        secho_mocker = self.get_file_report_mocker(
            mocker=mocker, files_type=self.SpelledFileType.INVALID
        )

        first_call = secho_mocker.mock_calls[0]
        assert "Files With Misspells" in first_call.args[0]
        assert first_call.kwargs == self.BRIGHT_RED_FG

        second_call = secho_mocker.mock_calls[1]
        assert "file1\nfile2" in second_call.args[0]
        assert second_call.kwargs == self.BRIGHT_RED_FG

        for i in range(2, len(secho_mocker.mock_calls)):
            assert "Files Without Misspells" not in secho_mocker.mock_calls[i].args

    def test_printing_malformed_release_notes(self, mocker):
        """
        Given -
            Malformed release-note.

        When -
            Printing files report.

        Then -
            Ensure 'Malformed Release Notes' is printed.
        """
        secho_mocker = self.get_file_report_mocker(
            mocker=mocker, files_type=self.SpelledFileType.INVALID_RELEASE_NOTES
        )

        first_call = secho_mocker.mock_calls[0]
        assert "Malformed Release Notes" in first_call.args[0]
        assert first_call.kwargs == self.BRIGHT_RED_FG

        second_call = secho_mocker.mock_calls[1]
        assert "file1\nfile2" in second_call.args[0]
        assert second_call.kwargs == self.BRIGHT_RED_FG

    def test_printing_mixed_report(self, mocker):
        """
        Given -
            Files reported as both valid/invalid spelled files.

        When -
            Printing files report.

        Then -
            Ensure both files misspelled and correctly spelled files are printed.
        """
        secho_mocker = self.get_file_report_mocker(
            mocker=mocker, files_type=self.SpelledFileType.BOTH_INVALID_AND_VALID
        )

        first_call = secho_mocker.mock_calls[0]
        assert "Files Without Misspells" in first_call.args[0]
        assert first_call.kwargs == self.GREEN_FG

        second_call = secho_mocker.mock_calls[1]
        assert "file1\nfile2" in second_call.args[0]
        assert second_call.kwargs == self.GREEN_FG

        third_call = secho_mocker.mock_calls[2]
        assert "Files With Misspells" in third_call.args[0]
        assert third_call.kwargs == self.BRIGHT_RED_FG

        forth_call = secho_mocker.mock_calls[3]
        assert "file1\nfile2" in forth_call.args[0]
        assert forth_call.kwargs == self.BRIGHT_RED_FG

    def test_printing_skip_non_xsoar_supported_file(
        self, mix_invalid_packs: List[Pack], mocker
    ):
        """
        Given:
            - A list of Packs (1 XSOAR-supported and 1 community-supported).

        When -
            Printing doc review report.

        Then:
            - Ensure that misspelled file in XSOAR-supported Pack is printed in report.
            - Ensure that misspelled file in community-supported Pack is skipped in report
        """

        t = TestDocReviewXSOAROnly()

        cmd_args: List[str] = []
        for pack in mix_invalid_packs:
            cmd_args.append("--input")
            cmd_args.append(pack.path)

            if is_xsoar_supported_pack(pack.path):
                expected_supported = (
                    f"Words that might be misspelled were found in {pack.path}"
                )
            else:
                expected_not_supported_readme = f"File '{pack.readme.path}' was skipped because it does not belong to an XSOAR-supported Pack"
                expected_not_supported_rn = f"File '{pack.release_notes[0].path}' was skipped because it does not belong to an XSOAR-supported Pack"

        doc_review_report = t.run_doc_review_cmd(cmd_args)

        report_output_lines = doc_review_report.output.splitlines()

        for line in report_output_lines:
            if re.match(self.README_SKIPPED_REGEX, line):
                assert expected_not_supported_readme == line

            if re.match(self.RN_SKIPPED_REGEX, line):
                assert expected_not_supported_rn == line

            if re.match(self.FILE_MISSPELL_FOUND_REGEX, line):
                assert expected_supported == line


WORDS = [
    ("invalidd", True, False),
    ("wordd", True, False),
    ("bizzaree", True, False),
    ("Heloo", True, False),
    ("tellllllllll", True, False),
    ("InvaliddWord", True, False),
    ("HelloWorrld", True, False),
    ("VeryGoooodddd", True, False),
    ("WordsTxxt", True, False),
    ("SommmmeTest", True, False),
    ("NotAGoooodSpelllledWordddd", True, False),
    ("invalid", False, False),
    ("word", False, False),
    ("old", False, False),
    ("bizzare", False, False),
    ("Hello", False, False),
    ("tell", False, False),
    ("InvalidWord", False, False),
    ("HelloWorld", False, False),
    ("VeryGood", False, False),
    ("SomeWord", False, False),
    ("SomeTest", False, False),
    ("InvalidWord", True, True),
    ("HelloWorld", True, True),
    ("VeryGoodBoy", True, True),
    ("SomeWord", True, True),
    ("SomeTest", True, True),
    ("AGoodSpelledWord", True, True),
    ("IPs", False, False),
    ("IPs**", False, False),
    ("invalid-word-kebabb-casee", True, True),
    ("valid-word-kebab-case", False, False),
]


@pytest.mark.parametrize("word, is_invalid_word, no_camelcase", WORDS)
def test_check_word_functionality(word, is_invalid_word, no_camelcase):
    """
    Given -
        Case1: A misspelled word (including CamelCase words).
        Case2: A valid spelled word (including CamelCase words).
        Case3: A valid spelled CamelCase word with no_camel_case=True

    When -
        Checking word's spelling.

    Then -
        Case1: Ensure the word is part of the 'unknown' words.
        Case2: Ensure the word is not part of the 'unknown' words.
        Case3: Ensure the CamelCase word is part of the 'unknown' words (which means it's a misspelled word!).
    """
    doc_reviewer = DocReviewer(no_camel_case=no_camelcase)
    doc_reviewer.check_word(word=word)
    if is_invalid_word:
        assert word in doc_reviewer.unknown_words
    else:
        assert word not in doc_reviewer.unknown_words


@pytest.mark.parametrize(
    "file_content, unknown_words, known_words_files_contents, review_success",
    [
        (
            "Added the nomnomone, nomnomtwo.",
            {},
            [{"nomnomone", "killaone"}, {"nomnomtwo", "killatwo"}],
            True,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            {"nomnomtwo": set()},
            [{"nomnomone", "killaone"}],
            False,
        ),
    ],
)
def test_having_two_known_words_files(
    repo, file_content, unknown_words, known_words_files_contents, review_success
):
    """
    Given:
        - A release notes file with two misspelled words.
        - Different variations of known_words files.

    When:
        - Running doc_reviewer with known_words_file_paths.

    Then:
        - Ensure the review result is appropriate.
        - Make sure a review has taken place.
        - Enusure the unknown words are as expected.
    """
    pack = repo.create_pack("test_pack")
    rn_file = pack.create_release_notes(version="1_0_0", content=file_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(
            file_paths=[rn_file.path], known_words_file_paths=known_words_file_paths
        )
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) > 0
        assert doc_reviewer.unknown_words == unknown_words


@pytest.mark.parametrize(
    "file_content, unknown_words, known_words_files_contents, packs_known_words_content, "
    "review_success",
    [
        (
            "Added the nomnomone, nomnomtwo.",
            set(),
            [["nomnomone"]],
            ["[known_words]", "nomnomtwo"],
            True,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            {"nomnomone"},
            [],
            ["[known_words]", "nomnomtwo"],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo, nomnomthree.",
            {"nomnomthree"},
            [["nomnomone"]],
            ["[known_words]", "nomnomtwo"],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo, nomnomthree.",
            set(),
            [["nomnomone"], ["nomnomthree"]],
            ["[known_words]", "nomnomtwo"],
            True,
        ),
    ],
)
def test_adding_known_words_from_pack(
    repo,
    file_content,
    unknown_words,
    known_words_files_contents,
    packs_known_words_content,
    review_success,
):
    """
    Given:
        - A release notes file with two misspelled words.
        - Different variations of known_words files, including pack-ignore known_words.

    When:
        - Running doc_reviewer with known_words_file_paths and load_known_words_from_pack option.

    Then:
        - Ensure the review result is appropriate.
        - Make sure a review has taken place.
        - Enusure the unknown words are as expected.
    """
    pack = repo.create_pack("test_pack")
    rn_file = pack.create_release_notes(version="1_0_0", content=file_content)
    pack.pack_ignore.write_list(packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(
            file_paths=[rn_file.path],
            known_words_file_paths=known_words_file_paths,
            load_known_words_from_pack=True,
        )
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) > 0
        assert set(doc_reviewer.unknown_words.keys()) == unknown_words


@pytest.mark.parametrize(
    "first_file_content, second_file_content, unknown_word_calls, known_words_files_contents, "
    "review_success, misspelled_files_num, packs_known_words_content, load_known_words_from_pack",
    [
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa.",
            set(),
            [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]],
            True,
            0,
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa.",
            [{"nomnomtwo": set()}],
            [["nomnomone", "killaone"]],
            False,
            1,
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa, killatwo.",
            [{"killatwo": set()}, {"nomnomtwo": set()}],
            [["nomnomone", "killaone"]],
            False,
            2,
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa.",
            [],
            [["nomnomone", "killaone"]],
            True,
            0,
            ["[known_words]", "nomnomtwo", "killatwo"],
            True,
        ),
    ],
)
def test_having_two_file_paths_same_pack(
    repo,
    mocker,
    first_file_content,
    second_file_content,
    unknown_word_calls,
    known_words_files_contents,
    review_success,
    misspelled_files_num,
    packs_known_words_content,
    load_known_words_from_pack,
):
    """
    Given:
        - 2 release notes files with two misspelled words each.
        - Different variations of known_words files, including pack-ignore known_words.

    When:
        - Running doc_reviewer with known_words_file_paths.

    Then:
        - Ensure the review result is appropriate.
        - Make sure a review has taken place.
        - Enusure the unknown words are as expected for each file.
    """
    pack = repo.create_pack("first_test_pack")
    first_rn_file = pack.create_release_notes(
        version="1_0_0", content=first_file_content
    )
    second_rn_file = pack.create_release_notes(
        version="1_0_1", content=second_file_content
    )
    pack.pack_ignore.write_list(packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    unknown_word_calls_with_mocker = []
    for unknown_words in unknown_word_calls:
        unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

    print_unknown_words = mocker.patch.object(DocReviewer, "print_unknown_words")

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(
            file_paths=[first_rn_file.path, second_rn_file.path],
            known_words_file_paths=known_words_file_paths,
            load_known_words_from_pack=load_known_words_from_pack,
        )
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(
            unknown_word_calls_with_mocker, any_order=True
        )
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize(
    "first_file_content, second_file_content, unknown_word_calls, known_words_files_contents, "
    "review_success, misspelled_files_num, first_packs_known_words_content, "
    "second_packs_known_words_content, load_known_words_from_pack",
    [
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killaone.",
            [],
            [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]],
            True,
            0,
            [],
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killaone.",
            [{"nomnomtwo": set()}],
            [["nomnomone", "killaone"]],
            False,
            1,
            [],
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killaone, killatwo.",
            [{"killatwo": set()}, {"nomnomtwo": set()}],
            [["nomnomone", "killaone"]],
            False,
            2,
            [],
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killaone, killatwo.",
            [{"nomnomtwo": set()}, {"killaone": set()}],
            [],
            False,
            2,
            ["[known_words]", "nomnomone", "killaone"],
            ["[known_words]", "nomnomtwo", "killatwo"],
            True,
        ),
        (
            "Added the killaone, nomnomone.",
            "Added the killatwo, nomnomtwo.",
            [],
            [],
            True,
            0,
            ["[known_words]", "nomnomone", "killaone"],
            ["[known_words]", "nomnomtwo", "killatwo"],
            True,
        ),
    ],
)
def test_having_two_file_paths_different_pack(
    repo,
    mocker,
    first_file_content,
    second_file_content,
    unknown_word_calls,
    known_words_files_contents,
    review_success,
    misspelled_files_num,
    first_packs_known_words_content,
    second_packs_known_words_content,
    load_known_words_from_pack,
):
    """
    Given:
        - 2 release notes files with two misspelled words each.
        - Different variations of known_words files, including pack-ignore known_words.

    When:
        - Running doc_reviewer with known_words_file_paths.

    Then:
        - Ensure the review result is appropriate.
        - Make sure a review has taken place.
        - Enusure the unknown words are as expected for each file.
    """
    first_pack = repo.create_pack("first_test_pack")
    second_pack = repo.create_pack("second_test_pack")
    first_rn_file = first_pack.create_release_notes(
        version="1_0_0", content=first_file_content
    )
    second_rn_file = second_pack.create_release_notes(
        version="1_0_1", content=second_file_content
    )
    first_pack.pack_ignore.write_list(first_packs_known_words_content)
    second_pack.pack_ignore.write_list(second_packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = first_pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    unknown_word_calls_with_mocker = []
    for unknown_words in unknown_word_calls:
        unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

    print_unknown_words = mocker.patch.object(DocReviewer, "print_unknown_words")

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(
            file_paths=[first_rn_file.path, second_rn_file.path],
            known_words_file_paths=known_words_file_paths,
            load_known_words_from_pack=load_known_words_from_pack,
        )
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(
            unknown_word_calls_with_mocker, any_order=True
        )
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize(
    "first_file_content, second_file_content, unknown_word_calls, known_words_files_contents, "
    "review_success, misspelled_files_num, packs_known_words_content, load_known_words_from_pack",
    [
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa.",
            [],
            [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]],
            True,
            0,
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa.",
            [{"nomnomtwo": set()}],
            [["nomnomone", "killaone"]],
            False,
            1,
            [],
            False,
        ),
        (
            "Added the nomnomone, nomnomtwo.",
            "Added the killa, killatwo.",
            [{"killatwo": set()}, {"nomnomtwo": set()}],
            [["nomnomone", "killaone"]],
            False,
            2,
            [],
            False,
        ),
    ],
)
def test_having_two_file_paths_not_same_pack(
    repo,
    mocker,
    first_file_content,
    second_file_content,
    unknown_word_calls,
    known_words_files_contents,
    review_success,
    misspelled_files_num,
    packs_known_words_content,
    load_known_words_from_pack,
):
    """
    Given:
        - 2 release notes files with two misspelled words each.
        - Different variations of known_words files, including pack-ignore known_words.

    When:
        - Running doc_reviewer with known_words_file_paths.

    Then:
        - Ensure the review result is appropriate.
        - Make sure a review has taken place.
        - Enusure the unknown words are as expected for each file.
    """
    pack = repo.create_pack("first_test_pack")
    first_rn_file = pack.create_release_notes(
        version="1_0_0", content=first_file_content
    )
    second_rn_file = pack.create_release_notes(
        version="1_0_1", content=second_file_content
    )
    pack.pack_ignore.write_list(packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    unknown_word_calls_with_mocker = []
    for unknown_words in unknown_word_calls:
        unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

    print_unknown_words = mocker.patch.object(DocReviewer, "print_unknown_words")

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(
            file_paths=[first_rn_file.path, second_rn_file.path],
            known_words_file_paths=known_words_file_paths,
            load_known_words_from_pack=load_known_words_from_pack,
        )
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(
            unknown_word_calls_with_mocker, any_order=True
        )
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize(
    "known_words_content, expected_known_words",
    [
        (["[known_words]", "wordament"], ["test_pack", "wordament"]),
        (["[known_words]"], ["test_pack"]),
        ([], ["test_pack"]),
    ],
)
def test_find_known_words_from_pack(repo, known_words_content, expected_known_words):
    """
    Given:
        - Pack's structure is correct and pack-ignore file is present.
            - Case A: pack-ignore file has known_words section with words.
            - Case B: pack-ignore file has known_words section without words.
            - Case C: pack-ignore file doesn't have a known_words section.

    When:
        - Running DocReviewer.find_known_words_from_pack.

    Then:
        - Ensure the found path result is appropriate.
        - Ensure the pack name (test_pack) is in the know words.
    """
    pack = repo.create_pack("test_pack")
    rn_file = pack.create_release_notes(version="1_0_0", content="Some release note")
    pack.pack_ignore.write_list(known_words_content)
    doc_reviewer = DocReviewer(file_paths=[])
    with ChangeCWD(repo.path):
        assert doc_reviewer.find_known_words_from_pack(rn_file.path) == (
            "Packs/test_pack/.pack-ignore",
            expected_known_words,
        )


def test_find_known_words_from_pack_ignore_integrations_name(repo):
    """
    Given:
        - Pack's structure is correct and pack-ignore file is present.

    When:
        - Running DocReviewer.find_known_words_from_pack.

    Then:
        - Ensure the found path result is appropriate.
        - Ensure the integrations name are ignored.
    """
    pack = repo.create_pack("test_pack")
    integration1 = pack.create_integration(name="first_integration")
    integration2 = pack.create_integration(name="second_integration")
    rn_file = pack.create_release_notes(
        version="1_0_0", content=f"{integration1.name}\n{integration2.name}"
    )
    doc_reviewer = DocReviewer(file_paths=[])
    with ChangeCWD(repo.path):
        found_known_words = doc_reviewer.find_known_words_from_pack(rn_file.path)[1]
        assert integration1.name in found_known_words
        assert integration2.name in found_known_words


def test_find_known_words_from_pack_ignore_commands_name(repo):
    """
    Given:
        - Pack's structure is correct and pack-ignore file is present.

    When:
        - Running DocReviewer.find_known_words_from_pack.

    Then:
        - Ensure the found path result is appropriate.
        - Ensure the commands names are ignored.
    """

    pack = repo.create_pack("test_pack")
    pack_integration_path = os.path.join(
        AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml"
    )
    valid_integration_yml = get_yaml(pack_integration_path, cache_clear=True)
    pack.create_integration(name="first_integration", yml=valid_integration_yml)
    rn_file = pack.create_release_notes(
        version="1_0_0", content="azure-hidden-command \n azure-get-indicators"
    )
    doc_reviewer = DocReviewer(file_paths=[])
    with ChangeCWD(repo.path):
        found_known_words = doc_reviewer.find_known_words_from_pack(rn_file.path)[1]
        assert "azure-hidden-command" in found_known_words
        assert "azure-get-indicators" in found_known_words


def test_find_known_words_from_pack_ignore_scripts_name(repo):
    """
    Given:
        - Pack's structure is correct and pack-ignore file is present.

    When:
        - Running DocReviewer.find_known_words_from_pack.

    Then:
        - Ensure the found path result is appropriate.
        - Ensure the scripts names are ignored.
    """

    pack = repo.create_pack("test_pack")
    script1 = pack.create_script(name="first_script")
    script2 = pack.create_script(name="second_script")
    rn_file = pack.create_release_notes(
        version="1_0_0", content=f"{script1.name}\n{script2.name}"
    )
    doc_reviewer = DocReviewer(file_paths=[])
    with ChangeCWD(repo.path):
        found_known_words = doc_reviewer.find_known_words_from_pack(rn_file.path)[1]
        assert script1.name in found_known_words
        assert script2.name in found_known_words


def test_find_known_words_from_pack_ignore_commons_scripts_name(repo):
    """
    Given:
        - Pack's structure is correct and pack-ignore file is present.
        - The scripts are in the old version (JS code), no Scripts' dir exists (only yml amd md files).

    When:
        - Running DocReviewer.find_known_words_from_pack.

    Then:
        - Ensure the found path result is appropriate.
        - Ensure the scripts names are ignored.
        - Ensure script readme name is not handled (bla.md)
    """

    pack = repo.create_pack("test_pack")
    script1_name = "script-first_script"
    # add a yml script directly into Scripts folder
    pack._create_yaml_based(
        name=script1_name,
        dir_path=f"{pack.path}//Scripts",
        content={"name": script1_name},
    )
    # add a .md file script directly into Scripts folder
    pack._create_text_based("bla.md", "", dir_path=Path(f"{pack.path}//Scripts"))
    # add a script into second_script folder
    script2 = pack.create_script(name="second_script")
    rn_file = pack.create_release_notes(
        version="1_0_0", content=f"{script1_name}\n{script2.name}"
    )
    doc_reviewer = DocReviewer(file_paths=[])

    with ChangeCWD(repo.path):
        found_known_words = doc_reviewer.find_known_words_from_pack(rn_file.path)[1]
        assert script1_name in found_known_words
        assert script2.name in found_known_words
        assert "bla.md" not in found_known_words


def test_camel_case_split():
    """
    Given
        - A CamelCase word

    When
        - Running camel_case_split on it.

    Then
        - Ensure result is a list of the split words in the camel case.
    """
    camel_1 = "ThisIsCamelCase"
    result = DocReviewer.camel_case_split(camel_1)
    assert isinstance(result, List)
    assert "This" in result
    assert "Is" in result
    assert "Camel" in result
    assert "Case" in result

    camel_2 = "thisIPIsAlsoCamel"
    result = DocReviewer.camel_case_split(camel_2)
    assert "this" in result
    assert "IP" in result
    assert "Is" in result
    assert "Also" in result
    assert "Camel" in result

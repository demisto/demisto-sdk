import pytest
from typing import List
from os import path

from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
from TestSuite.json_based import JSONBased
from demisto_sdk.commands.common.tools import find_type
from demisto_sdk.commands.common.constants import FileType


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
        doc_review = DocReviewer(file_path='test')
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
        doc_review = DocReviewer(file_path=valid_spelled_content_pack.path)
        doc_review.get_files_to_run_on()
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
        doc_review = DocReviewer(file_path=valid_spelled_content_pack.integrations[0].yml.path)
        doc_review.get_files_to_run_on()
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
            valid_spelled_content_pack.integrations[0].yml.path, valid_spelled_content_pack.scripts[0].yml.path
        ] + [rn.path for rn in valid_spelled_content_pack.release_notes]

        mocker.patch.object(
            DocReviewer,
            'gather_all_changed_files',
            return_value=changed_files_mock
        )
        doc_review = DocReviewer(file_path='', use_git=True)
        doc_review.get_files_to_run_on()
        assert doc_review.files == set(changed_files_mock)

    def test_find_only_supported_files(self, valid_spelled_content_pack):
        """
        Given -
            valid pack directory path.

        When -
            trying to find files from a directory.

        Then -
            Ensure the files that are found are only supported files.
        """
        doc_review = DocReviewer(file_path=valid_spelled_content_pack.path)
        doc_review.get_files_to_run_on()
        for file in doc_review.files:
            assert find_type(path=file) in doc_review.SUPPORTED_FILE_TYPES

    def test_find_unsupported_files(self, valid_spelled_content_pack):
        """
        Given -
            valid pack directory path.

        When -
            trying to find unsupported files from a directory.

        Then -
            Ensure that the unsupported files such as incident fields/layouts
            are not added for the files to do doc-review.
        """
        doc_review = DocReviewer(file_path=valid_spelled_content_pack.path)
        doc_review.get_files_to_run_on()

        for incident_field in valid_spelled_content_pack.incident_fields:
            assert incident_field.path not in doc_review.files
        for layout in valid_spelled_content_pack.layouts:
            assert layout.path not in doc_review.files


class TestDocReviewOnReleaseNotesOnly:
    """
    Tests scenarios which are related to executing doc-review with --release-notes
    """
    def test_doc_review_with_release_notes_is_skipped_on_invalid_yml_file(self, malformed_integration_yml):
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
            doc_reviewer = DocReviewer(file_path=_path, release_notes_only=True)
            assert doc_reviewer.run_doc_review()
            assert not doc_reviewer.files
        except ValueError as err:
            assert False, str(err)

    def test_doc_review_with_release_notes_is_skipped_on_invalid_json_file(self, malformed_incident_field: JSONBased):
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
            doc_reviewer = DocReviewer(file_path=_path, release_notes_only=True)
            assert doc_reviewer.run_doc_review()
            assert not doc_reviewer.files
        except ValueError as err:
            assert False, str(err)

    def test_doc_review_is_performed_only_on_release_notes(self, valid_spelled_content_pack):
        """
        Given
            - a pack

        When
            - Running doc-review with release-notes only.

        Then
            - Ensure The files that were doc-reviewed are only release-notes.
        """
        doc_reviewer = DocReviewer(file_path=valid_spelled_content_pack.path, release_notes_only=True)
        assert doc_reviewer.run_doc_review()
        assert doc_reviewer.files == {rn.path for rn in valid_spelled_content_pack.release_notes}

    def test_get_invalid_files_from_git_with_release_notes(
        self, mocker, malformed_integration_yml, malformed_incident_field
    ):
        """
        Given -
            malformed json/yml.

        When -
            Collecting files from git and release-notes is set to True.

        Then -
            Ensure that no exception/error is raised and that the malformed files were not added to the files to review.
        """
        mocker.patch.object(
            DocReviewer,
            'gather_all_changed_files',
            return_value=[
                malformed_integration_yml.path,
                malformed_incident_field.path
            ]
        )
        try:
            doc_reviewer = DocReviewer(file_path='', release_notes_only=True)
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
        assert DocReviewer(file_path='', release_notes_only=True).SUPPORTED_FILE_TYPES == [FileType.RELEASE_NOTES]


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

        doc_reviewer = DocReviewer(file_path=pack.path)
        assert not doc_reviewer.run_doc_review()
        assert doc_reviewer.found_misspelled
        assert len(doc_reviewer.files_with_misspells) == len(misspelled_files)
        assert doc_reviewer.files_with_misspells == misspelled_files

    def test_invalid_misspelled_files_with_no_failure(self, invalid_spelled_content_pack):
        """
        Given -
            Pack files with invalid content spelling and 'no_failure' input parameter set to True.

        When -
            Running doc-review on misspelled files.

        Then -
            Ensure doc-review still succeeds.
        """
        pack, _ = invalid_spelled_content_pack

        doc_reviewer = DocReviewer(file_path=pack.path, no_failure=True)
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

        doc_reviewer = DocReviewer(file_path=pack.path)
        assert doc_reviewer.run_doc_review()
        assert not doc_reviewer.found_misspelled
        assert len(doc_reviewer.files_with_misspells) == 0
        assert doc_reviewer.files_with_misspells == set()

    def test_invalid_spelled_files_with_known_words(self, known_words_path, misspelled_integration):
        """
        Given -
            misspelled integration yml and known_words.txt file path containing thw word 'invalidd'

        When -
            Running doc-review on misspelled files.

        Then -
            Ensure doc-review succeed and there aren't any misspelled files found.
        """
        doc_reviewer = DocReviewer(file_path=misspelled_integration.path, known_words_file_path=known_words_path)
        assert doc_reviewer.run_doc_review()
        assert not doc_reviewer.files_with_misspells


class TestDocReviewPrinting:
    """
    Test scenarios of doc-review printing.
    """
    MOCKED_FILES = ['file1', 'file2']
    GREEN_FG = {'fg': 'green'}
    BRIGHT_RED_FG = {'fg': 'bright_red'}

    class SpelledFileType:
        """
        INVALID = invalid spelled files.
        VALID - valid spelled files.
        BOTH_INVALID_AND_VALID - both invalid spelled files and valid spelled files are required.
        INVALID_RELEASE_NOTES - invalid release-notes files.
        """
        INVALID = 'invalid'
        VALID = 'valid'
        BOTH_INVALID_AND_VALID = 'invalid_and_valid'
        INVALID_RELEASE_NOTES = 'invalid_release_notes'

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
        doc_reviewer = DocReviewer(file_path='')

        if files_type == self.SpelledFileType.VALID:
            doc_reviewer.files_without_misspells = self.MOCKED_FILES
        elif files_type == self.SpelledFileType.INVALID:
            doc_reviewer.files_with_misspells = self.MOCKED_FILES
        elif files_type == self.SpelledFileType.INVALID_RELEASE_NOTES:
            doc_reviewer.malformed_rn_files = self.MOCKED_FILES
        else:
            doc_reviewer.files_with_misspells = self.MOCKED_FILES
            doc_reviewer.files_without_misspells = self.MOCKED_FILES

        secho_mocker = mocker.patch.object(click, 'secho')
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
        secho_mocker = self.get_file_report_mocker(mocker=mocker, files_type=self.SpelledFileType.VALID)

        first_call = secho_mocker.mock_calls[0]
        assert 'Files Without Misspells' in first_call.args[0]
        assert first_call.kwargs == self.GREEN_FG

        second_call = secho_mocker.mock_calls[1]
        assert 'file1\nfile2' in second_call.args[0]
        assert second_call.kwargs == self.GREEN_FG

        for i in range(2, len(secho_mocker.mock_calls)):
            assert 'Files With Misspells' not in secho_mocker.mock_calls[i].args

    def test_printing_invalid_spelled_files(self, mocker):
        """
        Given -
            Files reported as invalid spelled files.

        When -
            Printing files report.

        Then -
            Ensure only the files with misspells are printed.
        """
        secho_mocker = self.get_file_report_mocker(mocker=mocker, files_type=self.SpelledFileType.INVALID)

        first_call = secho_mocker.mock_calls[0]
        assert 'Files With Misspells' in first_call.args[0]
        assert first_call.kwargs == self.BRIGHT_RED_FG

        second_call = secho_mocker.mock_calls[1]
        assert 'file1\nfile2' in second_call.args[0]
        assert second_call.kwargs == self.BRIGHT_RED_FG

        for i in range(2, len(secho_mocker.mock_calls)):
            assert 'Files Without Misspells' not in secho_mocker.mock_calls[i].args

    def test_printing_invalid_spelled_release_notes(self, mocker):
        """
        Given -
            Release-notes reported as invalid spelled files.

        When -
            Printing files report.

        Then -
            Ensure only the release-notes files are printed.
        """
        secho_mocker = self.get_file_report_mocker(mocker=mocker, files_type=self.SpelledFileType.INVALID_RELEASE_NOTES)

        first_call = secho_mocker.mock_calls[0]
        assert 'Malformed Release Notes' in first_call.args[0]
        assert first_call.kwargs == self.BRIGHT_RED_FG

        second_call = secho_mocker.mock_calls[1]
        assert 'file1\nfile2' in second_call.args[0]
        assert second_call.kwargs == self.BRIGHT_RED_FG

    def test_printing_both_invalid_and_valid_spelled_files(self, mocker):
        """
        Given -
            Files reported as both valid/invalid spelled files.

        When -
            Printing files report.

        Then -
            Ensure both files misspelled and correctly spelled are printed.
        """
        secho_mocker = self.get_file_report_mocker(
            mocker=mocker, files_type=self.SpelledFileType.BOTH_INVALID_AND_VALID
        )

        first_call = secho_mocker.mock_calls[0]
        assert 'Files Without Misspells' in first_call.args[0]
        assert first_call.kwargs == self.GREEN_FG

        second_call = secho_mocker.mock_calls[1]
        assert 'file1\nfile2' in second_call.args[0]
        assert second_call.kwargs == self.GREEN_FG

        third_call = secho_mocker.mock_calls[2]
        assert 'Files With Misspells' in third_call.args[0]
        assert third_call.kwargs == self.BRIGHT_RED_FG

        forth_call = secho_mocker.mock_calls[3]
        assert 'file1\nfile2' in forth_call.args[0]
        assert forth_call.kwargs == self.BRIGHT_RED_FG


class TestWordsSpelling:
    """
    Test scenarios of doc-review of single words.
    """
    MISSPELLED_WORDS = [
        'invalidd',
        'wordd',
        'oldd',
        'bizzaree',
        'Heloo',
        'tellllllllll',
        'InvaliddWord',
        'HelloWorrld',
        'VeryGoooodddd',
        'WordsTxxt',
        'SommmmeTest',
        'NotAGoooodSpelllledWordddd'
    ]

    @pytest.mark.parametrize('misspelled_word', MISSPELLED_WORDS)
    def test_check_word_on_misspelled_words(self, misspelled_word):
        """
        Given -
            A misspelled word (including CamelCase words).

        When -
            Checking word's spelling.

        Then -
            Ensure the word is part of the 'unknown' words.
        """
        doc_reviewer = DocReviewer(file_path='')
        doc_reviewer.check_word(word=misspelled_word)
        assert misspelled_word in doc_reviewer.unknown_words

    VALID_SPELLED_WORDS = [
        'invalid',
        'word',
        'old',
        'bizzare',
        'Hello',
        'tell',
        'InvalidWord',
        'HelloWorld',
        'VeryGood',
        'SomeWord',
        'SomeTest',
        'AGoodSpelledWord'
    ]

    @pytest.mark.parametrize('valid_spelled_word', VALID_SPELLED_WORDS)
    def test_check_word_on_valid_spelled_words(self, valid_spelled_word):
        """
        Given -
            A valid spelled word (including CamelCase words).

        When -
            Checking word's spelling.

        Then -
            Ensure the word is not part of the 'unknown' words.
        """
        doc_reviewer = DocReviewer(file_path='')
        doc_reviewer.check_word(word=valid_spelled_word)
        assert valid_spelled_word not in doc_reviewer.unknown_words

    VALID_SPELLED_CAMELCASE_WORDS = [
        'InvalidWord',
        'HelloWorld',
        'VeryGoodBoy',
        'SomeWord',
        'SomeTest',
        'AGoodSpelledWord'
    ]

    @pytest.mark.parametrize('valid_camel_case_spelled_word', VALID_SPELLED_CAMELCASE_WORDS)
    def test_check_word_with_no_camelcase_on_valid_spelled_words_fails(self, valid_camel_case_spelled_word):
        """
        Given -
            A valid spelled CamelCase word.

        When -
            Checking word's spelling without considering CamelCase words.

        Then -
            Ensure the CamelCase word is part of the 'unknown' words (which means it's a misspelled word!).
        """
        doc_reviewer = DocReviewer(file_path='', no_camel_case=True)
        doc_reviewer.check_word(word=valid_camel_case_spelled_word)
        assert valid_camel_case_spelled_word in doc_reviewer.unknown_words


def test_camel_case_split():
    """
    Given
    - A CamelCase word

    When
    - Running camel_case_split on it.

    Then
    - Ensure result is a list of the split words in the camel case.
    """
    camel_1 = 'ThisIsCamelCase'
    result = DocReviewer.camel_case_split(camel_1)
    assert isinstance(result, List)
    assert 'This' in result
    assert 'Is' in result
    assert 'Camel' in result
    assert 'Case' in result

    camel_2 = 'thisIPIsAlsoCamel'
    result = DocReviewer.camel_case_split(camel_2)
    assert 'this' in result
    assert 'IP' in result
    assert 'Is' in result
    assert 'Also' in result
    assert 'Camel' in result

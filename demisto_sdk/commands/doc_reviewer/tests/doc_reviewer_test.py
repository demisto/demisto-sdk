import os
from pathlib import Path
from typing import List

import pytest

from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
from demisto_sdk.tests.constants_test import GIT_ROOT
from TestSuite.test_tools import ChangeCWD

FIRST_KNOWN_WORDS_PATH = 'known_words_for_tests.txt'  # Contains: nomnomone, killaone
SECOND_KNOWN_WORDS_PATH = 'another_known_words_for_tests.txt'  # Contains: nomnomtwo, killatwo


class TestUsingKnownWordsFiles:
    @staticmethod
    def setup():
        with open(FIRST_KNOWN_WORDS_PATH, 'w+') as file_to_check:
            file_to_check.write("nomnomone\nkillaone")

        with open(SECOND_KNOWN_WORDS_PATH, 'w+') as file_to_check:
            file_to_check.write("nomnomtwo\nkillatwo")

    @staticmethod
    def teardown():
        if os.path.isfile(FIRST_KNOWN_WORDS_PATH):
            os.remove(FIRST_KNOWN_WORDS_PATH)

        if os.path.isfile(SECOND_KNOWN_WORDS_PATH):
            os.remove(SECOND_KNOWN_WORDS_PATH)


class TestSingleInputFile(TestUsingKnownWordsFiles):
    FILE_PATH_TO_CHECK = 'some_file.md'

    def teardown(self):
        super(TestSingleInputFile, self).teardown()
        if os.path.isfile(self.FILE_PATH_TO_CHECK):
            os.remove(self.FILE_PATH_TO_CHECK)

    @pytest.mark.parametrize('file_content, unknown_words, known_words_file_paths, review_success',
                             [("This is nomnomone, nomnomtwo", {},
                               [FIRST_KNOWN_WORDS_PATH, SECOND_KNOWN_WORDS_PATH], True),
                              ("This is nomnomone, nomnomtwo", {"nomnomtwo": []},
                               [FIRST_KNOWN_WORDS_PATH], False)])
    def test_having_two_known_words_files(self, mocker, file_content, unknown_words, known_words_file_paths,
                                          review_success):
        with open(self.FILE_PATH_TO_CHECK, 'w+') as file_to_check:
            file_to_check.write(file_content)

        doc_reviewer = DocReviewer(file_paths=[self.FILE_PATH_TO_CHECK],
                                   known_words_file_paths=known_words_file_paths)

        release_notes_path = Path(f'SomePack/ReleaseNotes/{self.FILE_PATH_TO_CHECK}')
        mocker.patch.object(Path, '__new__', return_value=release_notes_path)

        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) > 0
        assert doc_reviewer.unknown_words == unknown_words

    @pytest.mark.parametrize('file_content, unknown_words, known_words_file_paths, review_success',
                             [("This is nomnomone, nomnomtwo", set(), [FIRST_KNOWN_WORDS_PATH], True),
                              ("This is nomnomone, nomnomtwo", {"nomnomone"}, [], False)])
    def test_adding_known_words_from_pack(self, mocker, file_content, unknown_words, known_words_file_paths,
                                          review_success):
        with open(self.FILE_PATH_TO_CHECK, 'w+') as file_to_check:
            file_to_check.write(file_content)

        release_notes_path = Path(f'SomePack/ReleaseNotes/{self.FILE_PATH_TO_CHECK}')
        mocker.patch.object(Path, '__new__', return_value=release_notes_path)
        mocker.patch.object(DocReviewer, 'find_known_words_from_pack', return_value=SECOND_KNOWN_WORDS_PATH)

        doc_reviewer = DocReviewer(file_paths=[self.FILE_PATH_TO_CHECK],
                                   known_words_file_paths=known_words_file_paths,
                                   load_known_words_from_pack=True)

        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) > 0
        assert set(doc_reviewer.unknown_words.keys()) == unknown_words


class TestTwoInputFiles(TestUsingKnownWordsFiles):
    FIRST_FILE_PATH = 'some_file.md'
    SECOND_FILE_PATH = 'some_other_file.md'

    def teardown(self):
        super(TestTwoInputFiles, self).teardown()
        if os.path.isfile(self.FIRST_FILE_PATH):
            os.remove(self.FIRST_FILE_PATH)

        if os.path.isfile(self.SECOND_FILE_PATH):
            os.remove(self.SECOND_FILE_PATH)

    @pytest.mark.parametrize('first_path, second_path, first_file_content, second_file_content, unknown_word_calls, '
                             'known_words_file_paths, review_success, misspelled_files_num',
                             [('SomePack/ReleaseNotes', 'SomePack/ReleaseNotes',  # Same pack
                               "This is nomnomone, nomnomtwo", "This is killa", [],
                               [FIRST_KNOWN_WORDS_PATH, SECOND_KNOWN_WORDS_PATH], True, 0),
                              ('SomePack/ReleaseNotes', 'SomePack/ReleaseNotes',  # Same pack
                               "This is nomnomone, nomnomtwo", "This is killa", [{"nomnomtwo": []}],
                               [FIRST_KNOWN_WORDS_PATH], False, 1),
                              ('SomePack/ReleaseNotes', 'SomePack/ReleaseNotes',  # Same pack
                               "This is nomnomone, nomnomtwo", "This is killa, killatwo", [{"killatwo": []},
                                                                                           {"nomnomtwo": []}],
                               [FIRST_KNOWN_WORDS_PATH], False, 2),
                              ('SomePack/ReleaseNotes', 'SomeOtherPack/ReleaseNotes',  # not same pack
                               "This is nomnomone, nomnomtwo", "This is killa", [],
                               [FIRST_KNOWN_WORDS_PATH, SECOND_KNOWN_WORDS_PATH], True, 0),
                              ('SomePack/ReleaseNotes', 'SomeOtherPack/ReleaseNotes',  # not same pack
                               "This is nomnomone, nomnomtwo", "This is killa", [{"nomnomtwo": []}],
                               [FIRST_KNOWN_WORDS_PATH], False, 1),
                              ('SomePack/ReleaseNotes', 'SomeOtherPack/ReleaseNotes',  # not same pack
                               "This is nomnomone, nomnomtwo", "This is killa, killatwo", [{"killatwo": []},
                                                                                           {"nomnomtwo": []}],
                               [FIRST_KNOWN_WORDS_PATH], False, 2)
                              ])
    def test_having_two_file_paths(self, mocker, first_path, second_path, first_file_content,
                                   second_file_content, unknown_word_calls, known_words_file_paths, review_success,
                                   misspelled_files_num):
        with open(self.FIRST_FILE_PATH, 'w+') as file_to_check:
            file_to_check.write(first_file_content)

        with open(self.SECOND_FILE_PATH, 'w+') as file_to_check:
            file_to_check.write(second_file_content)

        unknown_word_calls_with_mocker = []
        for unknown_words in unknown_word_calls:
            unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

        first_release_notes_path = Path(f'{first_path}/{self.FIRST_FILE_PATH}')
        second_release_notes_path = Path(f'{second_path}/{self.SECOND_FILE_PATH}')
        mocker.patch.object(Path, '__new__', side_effect=[first_release_notes_path, second_release_notes_path])
        print_unknown_words = mocker.patch.object(DocReviewer, 'print_unknown_words')

        doc_reviewer = DocReviewer(file_paths=[self.FIRST_FILE_PATH, self.SECOND_FILE_PATH],
                                   known_words_file_paths=known_words_file_paths)

        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(unknown_word_calls_with_mocker, any_order=True)
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num

    @pytest.mark.parametrize('first_path, second_path, first_file_content, second_file_content, unknown_word_calls, '
                             'known_words_file_paths, packs_unknown_words, review_success, misspelled_files_num',
                             [('SomePack/ReleaseNotes', 'SomePack/ReleaseNotes',  # same pack
                               "This is nomnomone, nomnomtwo", "This is killaone, killatwo", [],
                               [FIRST_KNOWN_WORDS_PATH], [SECOND_KNOWN_WORDS_PATH, SECOND_KNOWN_WORDS_PATH], True, 0),
                              ('SomePack/ReleaseNotes', 'SomeOtherPack/ReleaseNotes',  # not same pack
                               "This is nomnomone, nomnomtwo", "This is killaone, killatwo",
                               [{"nomnomtwo": []}, {"killaone": []}],
                                 [], [FIRST_KNOWN_WORDS_PATH, SECOND_KNOWN_WORDS_PATH], False, 2)
                              ])
    def test_two_files_adding_known_words_from_pack(self, mocker, first_path, second_path, first_file_content,
                                                    second_file_content, unknown_word_calls, known_words_file_paths,
                                                    packs_unknown_words, review_success, misspelled_files_num):
        with open(self.FIRST_FILE_PATH, 'w+') as file_to_check:
            file_to_check.write(first_file_content)

        with open(self.SECOND_FILE_PATH, 'w+') as file_to_check:
            file_to_check.write(second_file_content)

        unknown_word_calls_with_mocker = []
        for unknown_words in unknown_word_calls:
            unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

        first_release_notes_path = Path(f'{first_path}/{self.FIRST_FILE_PATH}')
        second_release_notes_path = Path(f'{second_path}/{self.SECOND_FILE_PATH}')
        mocker.patch.object(Path, '__new__', side_effect=[first_release_notes_path, second_release_notes_path])
        print_unknown_words = mocker.patch.object(DocReviewer, 'print_unknown_words', side_effect=DocReviewer.print_unknown_words)
        print(f"PACKS known words {packs_unknown_words}")
        mocker.patch.object(DocReviewer, 'find_known_words_from_pack', side_effect=packs_unknown_words)

        doc_reviewer = DocReviewer(file_paths=[self.FIRST_FILE_PATH, self.SECOND_FILE_PATH],
                                   known_words_file_paths=known_words_file_paths,
                                   load_known_words_from_pack=True)

        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(unknown_word_calls_with_mocker, any_order=True)
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize('repo_path, file_path, expected_result',
                         [(f"{GIT_ROOT}/demisto_sdk/tests/test_files", "Packs/DummyPack/ReleaseNotes/1_0_1.md",
                           "Packs/DummyPack/known_words.txt"),
                          (f"{GIT_ROOT}/demisto_sdk/tests/test_files", "Packs/CortexXDR/ReleaseNotes/1_1_1.md",
                           ""),  # No known_words file there.
                          (".", "some_fake_path", "")])
def test_find_known_words_from_pack(repo_path, file_path, expected_result):
    with ChangeCWD(repo_path):
        doc_reviewer = DocReviewer(file_paths=[])
        assert doc_reviewer.find_known_words_from_pack(file_path) == expected_result


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

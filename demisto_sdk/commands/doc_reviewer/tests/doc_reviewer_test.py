from typing import List

import pytest

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer

FIRST_KNOWN_WORDS_PATH = 'known_words_for_tests.txt'
SECOND_KNOWN_WORDS_PATH = 'another_known_words_for_tests.txt'


@pytest.mark.parametrize('file_content, unknown_words, known_words_file_paths, review_success',
                         [("This is nomnom, nomnomtwo", {}, [FIRST_KNOWN_WORDS_PATH, SECOND_KNOWN_WORDS_PATH], True),
                          ("This is nomnom, nomnomtwo", {"nomnomtwo"}, [FIRST_KNOWN_WORDS_PATH], False)])
def test_having_two_known_words_files(mocker, file_content, unknown_words, known_words_file_paths, review_success):
    file_path_to_check = 'some_file.md'
    with open(file_path_to_check, 'w+') as file_to_check:
        file_to_check.write(file_content)

    doc_reviewer = DocReviewer(file_paths=[file_path_to_check],
                               known_words_file_paths=known_words_file_paths)
    mocker.patch('demisto_sdk.commands.common.tools.find_type', return_value=FileType.RELEASE_NOTES)

    assert doc_reviewer.run_doc_review() == review_success
    assert len(doc_reviewer.files) > 0
    assert doc_reviewer.unknown_words == unknown_words


def test_having_multiple_file_paths():
    pass


def test_adding_known_words_from_pack():
    pass


def test_files_from_different_packs():
    pass


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

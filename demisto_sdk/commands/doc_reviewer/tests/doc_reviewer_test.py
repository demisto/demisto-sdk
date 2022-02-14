from typing import List

import pytest

from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
from TestSuite.json_based import JSONBased
from TestSuite.test_tools import ChangeCWD


def test_doc_review_with_release_notes_is_skipped_on_invalid_yml_file(malformed_integration_yml):
    """
    Given -
        malformed yml integration file.

    When -
        Calling doc-review with --release-notes.

    Then -
        Ensure that no exception/error is raised and that the malformed files were not added to the files for review.
    """
    path = malformed_integration_yml.path

    try:
        doc_reviewer = DocReviewer(file_paths=[path], release_notes_only=True)
        assert doc_reviewer.run_doc_review()
        assert not doc_reviewer.files
    except ValueError as err:
        assert False, str(err)


def test_doc_review_with_release_notes_is_skipped_on_invalid_json_file(malformed_incident_field: JSONBased):
    """
    Given -
        malformed json incident field.

    When -
        Calling doc-review with --release-notes.

    Then -
        Ensure that no exception/error is raised and that the malformed files were not added to the files for review.
    """
    path = malformed_incident_field.path

    try:
        doc_reviewer = DocReviewer(file_paths=[path], release_notes_only=True)
        assert doc_reviewer.run_doc_review()
        assert not doc_reviewer.files
    except ValueError as err:
        assert False, str(err)


def test_get_files_from_git_with_invalid_files(mocker, malformed_integration_yml, malformed_incident_field):
    """
    Given -
        malformed json/yml.

    When -
        Collecting files from git.

    Then -
        Ensure that no exception/error is raised and that the malformed files were not added to the files for review.
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
        doc_reviewer = DocReviewer(file_paths=[], release_notes_only=True)
        doc_reviewer.get_files_from_git()
        assert not doc_reviewer.files
    except ValueError as err:
        assert False, str(err)


@pytest.mark.parametrize('file_content, unknown_words, known_words_files_contents, review_success',
                         [("This is nomnomone, nomnomtwo", {},
                           [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]], True),
                          ("This is nomnomone, nomnomtwo", {"nomnomtwo": []},
                           [["nomnomone", "killaone"]], False)])
def test_having_two_known_words_files(repo, file_content, unknown_words, known_words_files_contents,
                                      review_success):
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
    pack = repo.create_pack('test_pack')
    rn_file = pack.create_release_notes(version='1_0_0', content=file_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(file_paths=[rn_file.path], known_words_file_paths=known_words_file_paths)
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) > 0
        assert doc_reviewer.unknown_words == unknown_words


@pytest.mark.parametrize('file_content, unknown_words, known_words_files_contents, packs_known_words_content, '
                         'review_success',
                         [("This is nomnomone, nomnomtwo", set(), [["nomnomone"]], ["[known_words]", "nomnomtwo"], True),
                          ("This is nomnomone, nomnomtwo", {"nomnomone"}, [], ["[known_words]", "nomnomtwo"], False),
                          ("This is nomnomone, nomnomtwo, nomnomthree", {"nomnomthree"}, [["nomnomone"]],
                           ["[known_words]", "nomnomtwo"], False),
                          ("This is nomnomone, nomnomtwo, nomnomthree", set(),
                           [["nomnomone"], ["nomnomthree"]], ["[known_words]", "nomnomtwo"], True)])
def test_adding_known_words_from_pack(repo, file_content, unknown_words, known_words_files_contents,
                                      packs_known_words_content, review_success):
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
    pack = repo.create_pack('test_pack')
    rn_file = pack.create_release_notes(version='1_0_0', content=file_content)
    pack.pack_ignore.write_list(packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(file_paths=[rn_file.path],
                                   known_words_file_paths=known_words_file_paths,
                                   load_known_words_from_pack=True)
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) > 0
        assert set(doc_reviewer.unknown_words.keys()) == unknown_words


@pytest.mark.parametrize('first_file_content, second_file_content, unknown_word_calls, known_words_files_contents, '
                         'review_success, misspelled_files_num, packs_known_words_content, load_known_words_from_pack',
                         [("This is nomnomone, nomnomtwo", "This is killa", [],
                           [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]], True, 0, [], False),
                          ("This is nomnomone, nomnomtwo", "This is killa", [{"nomnomtwo": []}],
                           [["nomnomone", "killaone"]], False, 1, [], False),
                          ("This is nomnomone, nomnomtwo", "This is killa, killatwo", [{"killatwo": []},
                                                                                       {"nomnomtwo": []}],
                           [["nomnomone", "killaone"]], False, 2, [], False),
                          ("This is nomnomone, nomnomtwo", "This is killa", [],
                           [["nomnomone", "killaone"]], True, 0, ["[known_words]", "nomnomtwo", "killatwo"], True)
                          ])
def test_having_two_file_paths_same_pack(repo, mocker, first_file_content, second_file_content, unknown_word_calls,
                                         known_words_files_contents, review_success, misspelled_files_num,
                                         packs_known_words_content, load_known_words_from_pack):
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
    pack = repo.create_pack('first_test_pack')
    first_rn_file = pack.create_release_notes(version='1_0_0', content=first_file_content)
    second_rn_file = pack.create_release_notes(version='1_0_1', content=second_file_content)
    pack.pack_ignore.write_list(packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    unknown_word_calls_with_mocker = []
    for unknown_words in unknown_word_calls:
        unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

    print_unknown_words = mocker.patch.object(DocReviewer, 'print_unknown_words')

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(file_paths=[first_rn_file.path, second_rn_file.path],
                                   known_words_file_paths=known_words_file_paths,
                                   load_known_words_from_pack=load_known_words_from_pack)
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(unknown_word_calls_with_mocker, any_order=True)
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize('first_file_content, second_file_content, unknown_word_calls, known_words_files_contents, '
                         'review_success, misspelled_files_num, first_packs_known_words_content, '
                         'second_packs_known_words_content, load_known_words_from_pack',
                         [("This is nomnomone, nomnomtwo", "This is killaone", [],
                           [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]], True, 0, [], [], False),
                          ("This is nomnomone, nomnomtwo", "This is killaone", [{"nomnomtwo": []}],
                           [["nomnomone", "killaone"]], False, 1, [], [], False),
                          ("This is nomnomone, nomnomtwo", "This is killaone, killatwo", [{"killatwo": []},
                                                                                          {"nomnomtwo": []}],
                           [["nomnomone", "killaone"]], False, 2, [], [], False),

                          ("This is nomnomone, nomnomtwo", "This is killaone, killatwo", [{"nomnomtwo": []},
                                                                                          {"killaone": []}],
                           [], False, 2, ["[known_words]", "nomnomone", "killaone"],
                           ["[known_words]", "nomnomtwo", "killatwo"], True),

                          ("This is killaone, nomnomone", "This is killatwo, nomnomtwo", [],
                           [], True, 0, ["[known_words]", "nomnomone", "killaone"],
                           ["[known_words]", "nomnomtwo", "killatwo"], True),
                          ])
def test_having_two_file_paths_different_pack(repo, mocker, first_file_content, second_file_content, unknown_word_calls,
                                              known_words_files_contents, review_success, misspelled_files_num,
                                              first_packs_known_words_content, second_packs_known_words_content, load_known_words_from_pack):
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
    first_pack = repo.create_pack('first_test_pack')
    second_pack = repo.create_pack('second_test_pack')
    first_rn_file = first_pack.create_release_notes(version='1_0_0', content=first_file_content)
    second_rn_file = second_pack.create_release_notes(version='1_0_1', content=second_file_content)
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

    print_unknown_words = mocker.patch.object(DocReviewer, 'print_unknown_words')

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(file_paths=[first_rn_file.path, second_rn_file.path],
                                   known_words_file_paths=known_words_file_paths,
                                   load_known_words_from_pack=load_known_words_from_pack)
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(unknown_word_calls_with_mocker, any_order=True)
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize('first_file_content, second_file_content, unknown_word_calls, known_words_files_contents, '
                         'review_success, misspelled_files_num, packs_known_words_content, load_known_words_from_pack',
                         [("This is nomnomone, nomnomtwo", "This is killa", [],
                           [["nomnomone", "killaone"], ["nomnomtwo", "killatwo"]], True, 0, [], False),
                          ("This is nomnomone, nomnomtwo", "This is killa", [{"nomnomtwo": []}],
                           [["nomnomone", "killaone"]], False, 1, [], False),
                          ("This is nomnomone, nomnomtwo", "This is killa, killatwo", [{"killatwo": []},
                                                                                       {"nomnomtwo": []}],
                           [["nomnomone", "killaone"]], False, 2, [], False),
                          ])
def test_having_two_file_paths_not_same_pack(repo, mocker, first_file_content, second_file_content, unknown_word_calls,
                                             known_words_files_contents, review_success, misspelled_files_num,
                                             packs_known_words_content, load_known_words_from_pack):
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
    pack = repo.create_pack('first_test_pack')
    first_rn_file = pack.create_release_notes(version='1_0_0', content=first_file_content)
    second_rn_file = pack.create_release_notes(version='1_0_1', content=second_file_content)
    pack.pack_ignore.write_list(packs_known_words_content)
    known_words_file_paths = []
    for index, known_words_file_contents in enumerate(known_words_files_contents):
        known_words_file = pack._create_text_based(f"known_words_{index}.txt")
        known_words_file.write_list(known_words_file_contents)
        known_words_file_paths.append(known_words_file.path)

    unknown_word_calls_with_mocker = []
    for unknown_words in unknown_word_calls:
        unknown_word_calls_with_mocker.append(mocker.call(unknown_words=unknown_words))

    print_unknown_words = mocker.patch.object(DocReviewer, 'print_unknown_words')

    with ChangeCWD(repo.path):
        doc_reviewer = DocReviewer(file_paths=[first_rn_file.path, second_rn_file.path],
                                   known_words_file_paths=known_words_file_paths,
                                   load_known_words_from_pack=load_known_words_from_pack)
        assert doc_reviewer.run_doc_review() == review_success
        assert len(doc_reviewer.files) == 2
        print_unknown_words.assert_has_calls(unknown_word_calls_with_mocker, any_order=True)
        assert len(doc_reviewer.files_with_misspells) == misspelled_files_num


@pytest.mark.parametrize('known_words_content, expected_known_words',
                         [(['[known_words]', 'wordament'], ['wordament']),
                          (['[known_words]'], []),
                          ([], [])])
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
    """
    pack = repo.create_pack('test_pack')
    rn_file = pack.create_release_notes(version='1_0_0', content='Some release note')
    pack.pack_ignore.write_list(known_words_content)
    doc_reviewer = DocReviewer(file_paths=[])
    with ChangeCWD(repo.path):
        assert doc_reviewer.find_known_words_from_pack(rn_file.path) == ('Packs/test_pack/.pack-ignore',
                                                                         expected_known_words)


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

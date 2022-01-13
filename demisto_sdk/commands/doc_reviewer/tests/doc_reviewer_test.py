from typing import List

import pytest
from _pytest.fixtures import FixtureRequest

from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
from TestSuite.pack import Pack
from _pytest.tmpdir import TempPathFactory
from conftest import get_pack, get_playbook, get_integration

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


def test_doc_review_is_performed_only_on_release_notes(pack: Pack):
    """
    Given
        - a pack

    When
        - Running doc-review with release-notes only.

    Then
        - Ensure The files that were doc-reviewed are only release-notes.
    """
    doc_reviewer = DocReviewer(file_path=pack.path, release_notes_only=True)
    assert doc_reviewer.run_doc_review()
    assert doc_reviewer.files == pack.release_notes
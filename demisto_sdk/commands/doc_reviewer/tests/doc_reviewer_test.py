from typing import List

import pytest

from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer
from TestSuite.json_based import JSONBased
from TestSuite.yml import YAML


@pytest.fixture()
def malformed_integration_yml(integration) -> YAML:
    integration.yml.write("1: 2\n//")
    return integration.yml


@pytest.fixture()
def malformed_incident_field(pack) -> JSONBased:
    incident_field = pack.create_incident_field("malformed")
    incident_field.write_as_text("{\n '1': '1'")
    return incident_field


def test_doc_review_with_release_notes_is_skipped_on_invalid_yml_file(malformed_integration_yml):
    """
    Given -
        malformed yml integration file.

    When -
        Calling doc-review with --release-notes.

    Then -
        Ensure that no exception/error is raised.
    """
    path = malformed_integration_yml.path

    try:
        doc_reviewer = DocReviewer(file_path=path, release_notes_only=True)
        assert doc_reviewer.run_doc_review()
        assert not doc_reviewer.files
    except ValueError as err:
        assert False, str(err)


def test_doc_review_with_release_notes_is_skipped_on_invalid_json_file(malformed_incident_field: JSONBased):
    """
    Given -
        malformed json incident type.

    When -
        Calling doc-review with --release-notes.

    Then -
        Ensure that no exception/error is raised.
    """
    path = malformed_incident_field.path

    try:
        doc_reviewer = DocReviewer(file_path=path, release_notes_only=True)
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

    doc_reviewer = DocReviewer(file_path='', release_notes_only=True)
    doc_reviewer.get_files_from_git()
    assert not doc_reviewer.files


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

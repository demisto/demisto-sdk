from typing import List

import pytest


from demisto_sdk.commands.doc_reviewer.doc_reviewer import DocReviewer


def doc_reviewer(
    file_path: str,
    known_words_file_path: str = None,
    no_camel_case: bool = False,
    no_failure: bool = False,
    expand_dictionary: bool = False,
    templates: bool = False,
    use_git: bool = False,
    prev_ver: str = None,
    release_notes_only: bool = False
) -> DocReviewer:

    return DocReviewer(
        file_path=file_path,
        known_words_file_path=known_words_file_path,
        no_camel_case=no_camel_case,
        no_failure=no_failure,
        expand_dictionary=expand_dictionary,
        templates=templates,
        use_git=use_git,
        prev_ver=prev_ver,
        release_notes_only=release_notes_only
    )


@pytest.fixture()
def doc_reviewer_with_malformed_integration_yml(integration) -> DocReviewer:
    integration.yml.write("1: 2\n//")
    return doc_reviewer(file_path=integration.yml.path, release_notes_only=True)


@pytest.fixture()
def doc_reviewer_with_malformed_incident_field(pack) -> DocReviewer:
    incident_field = pack.create_incident_field("malformed")
    incident_field.write_as_text("{\n '1': '1'")
    return doc_reviewer(file_path=incident_field.path, release_notes_only=True)


def test_doc_review_with_release_notes_is_skipped_on_invalid_yml_file(
    doc_reviewer_with_malformed_integration_yml: DocReviewer
):
    """
    Given -
        malformed yml integration file.

    When -
        Calling doc-review with --release-notes.

    Then -
        Ensure that no exception/error is raised.
    """
    assert doc_reviewer_with_malformed_integration_yml.run_doc_review(), (
        f"doc-review --release-notes failed on file - {doc_reviewer_with_malformed_integration_yml.file_path}"
    )


def test_doc_review_with_release_notes_is_skipped_on_invalid_json_file(
    doc_reviewer_with_malformed_incident_field: DocReviewer
):
    """
    Given -
        malformed json incident type.

    When -
        Calling doc-review with --release-notes.

    Then -
        Ensure that no exception/error is raised.
    """
    assert doc_reviewer_with_malformed_incident_field.run_doc_review(), (
        f"doc-review --release-notes failed on file - {doc_reviewer_with_malformed_incident_field.file_path}"
    )


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

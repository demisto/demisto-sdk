import json
import os
from queue import Queue
from unittest import mock

import pytest
import responses

from demisto_sdk.commands.test_content.execute_test_content import (
    COVERAGE_REPORT_COMMENT, SKIPPED_CONTENT_COMMENT, _add_pr_comment)


class MockTestResults:
    playbook_skipped_integration = {'demo integration'}
    failed_playbooks = False

    @staticmethod
    def print_test_summary(is_ami, logging_module):
        return

    @staticmethod
    def create_result_files():
        return


class MockBuildContext:
    instances_ips = {}
    unmockable_tests_to_run = Queue()
    mockable_tests_to_run = Queue()
    build_name = 'mock'
    is_nightly = False
    tests_data_keeper = MockTestResults
    isAMI = False


MOCK_ENV_VARIABLES = {
    'CONTENT_GITHUB_TOKEN': '123456',
    'CI_COMMIT_BRANCH': 'mock_branch',
    'CI_COMMIT_SHA': '1234567890abcdef',
    'UT_JOB_ID': '123456'
}


# https://github.com/getsentry/responses
@pytest.mark.parametrize('comment', [
    'The following integrations/tests were collected by the CI build but are currently skipped. '
    'The collected tests are related to this pull request and might be critical:\n- demo integration',

    'Link to the coverage report of the integration:\n '
    'https://xsoar.docs.pan.run/-/content/-/jobs/123456/artifacts/artifacts/coverage_report/html/index.html'
])
@responses.activate
def test_add_pr_comment(mocker, comment):
    """
    When:
        - A job in content pipeline is running.

    Given:
        - A pr in content.
        - A comment to add.

    Then:
        - Verify that comment was added as expected (and remove if needed)
    """

    results = {}

    def mock_handle_github_response(response, logging_module):
        return response.json()

    def mock_post_response(request):
        body = json.loads(request.body)
        headers = {'request-id': '123456789'}
        results.update(body)
        return 200, headers, json.dumps(body)

    # mocker.patch('demisto_sdk.commands.test_content.execute_test_content.BuildContext', return_value=MockBuildContext)
    mocker.patch('demisto_sdk.commands.test_content.execute_test_content._handle_github_response',
                 side_effect=mock_handle_github_response)
    url = 'https://api.github.com/search/issues'
    query = '?q=1234567890abcdef+repo:demisto/content+org:demisto+is:pr+is:open+head:mock_branch+is:open'

    with mock.patch.dict(os.environ, MOCK_ENV_VARIABLES, clear=True):
        responses.add(responses.GET, url + query,
                      json={'total_count': 1, 'items': [{'comments_url': 'https://api.github.com/search/issues/1'}]})
        responses.add(responses.GET, 'https://api.github.com/search/issues/1', json=[
            {'body': SKIPPED_CONTENT_COMMENT, 'url': 'https://github.com/comment_123456'},
            {'body': COVERAGE_REPORT_COMMENT, 'url': 'https://github.com/comment_123456'}
        ])
        responses.add(responses.DELETE, 'https://github.com/comment_123456')
        responses.add_callback(responses.POST, 'https://api.github.com/search/issues/1',
                               callback=mock_post_response, content_type='application/json')

        _add_pr_comment(comment, "")

    assert comment == results.get('body')

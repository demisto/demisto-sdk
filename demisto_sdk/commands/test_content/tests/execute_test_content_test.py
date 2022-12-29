import os
from unittest import mock

import pytest
import requests_mock

from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.test_content.execute_test_content import (
    COVERAGE_REPORT_COMMENT,
    SKIPPED_CONTENT_COMMENT,
    _add_pr_comment,
)

json = JSON_Handler()


MOCK_ENV_VARIABLES = {
    "XSOAR_BOT_TEST_CONTENT": "123456",
    "CI_COMMIT_BRANCH": "mock_branch",
    "CI_COMMIT_SHA": "1234567890abcdef",
    "UT_JOB_ID": "123456",
}


@pytest.mark.parametrize(
    "comment, skipped_flow, coverage_flow",
    [
        (
            "The following integrations/tests were collected by the CI build but are currently skipped. "
            "The collected tests are related to this pull request and might be critical:\n- demo integration",
            True,
            False,
        ),
        (
            "Link to the coverage report of the integration:\n "
            "https://xsoar.docs.pan.run/-/content/-/jobs/123456/artifacts/artifacts/coverage_report/html/index.html",
            False,
            True,
        ),
    ],
)
def test_add_pr_comment(mocker, comment, skipped_flow, coverage_flow):
    """
    When:
        - A job in content pipeline is running.

    Given:
        - A pr in content.
        - A comment to add.

    Then:
        - Verify that comment was added as expected (and remove if needed)
    """

    def mock_handle_github_response(response, logging_module):
        return response.json() if response.text else ""

    mocker.patch(
        "demisto_sdk.commands.test_content.execute_test_content._handle_github_response",
        side_effect=mock_handle_github_response,
    )
    url = "https://api.github.com/search/issues"
    query = "?q=1234567890abcdef+repo:demisto/content+org:demisto+is:pr+is:open+head:mock_branch+is:open"

    with mock.patch.dict(os.environ, MOCK_ENV_VARIABLES, clear=True):
        with requests_mock.Mocker() as m:
            m.get(
                url + query,
                json={
                    "total_count": 1,
                    "items": [
                        {"comments_url": "https://api.github.com/search/issues/1"}
                    ],
                },
            )
            m.get(
                "https://api.github.com/search/issues/1",
                json=[
                    {
                        "body": SKIPPED_CONTENT_COMMENT,
                        "url": "https://github.com/comment_12345",
                    },
                    {
                        "body": COVERAGE_REPORT_COMMENT,
                        "url": "https://github.com/comment_67890",
                    },
                ],
            )
            skipped_deleted = m.delete("https://github.com/comment_12345")
            coverage_deleted = m.delete("https://github.com/comment_67890")
            result = m.post("https://api.github.com/search/issues/1")

            _add_pr_comment(comment, "")

    assert json.loads(result.last_request.text).get("body") == comment
    assert skipped_deleted.called == skipped_flow
    assert coverage_deleted.called == coverage_flow

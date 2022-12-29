import pytest
from circle_ci_client import API_BASE_URL, PROJECT_SLUG, CircleCIClient

WORKFLOW_ID = "1"
UNIT_TEST_JOB_NUMBER = 1
INTEGRATION_TEST_JOB_NUMBER = 2
VALIDATION_JOB_NUMBER = 3
PRE_COMMIT_JOB_NUMBER = 4
VALIDATION_STEP_AND_INDEX = 0
VALIDATION_ALLOCATION_ID = "123"
PIPELINE_NUM = 1234


CIRCLE_CI_API_MOCKS = [
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V2}/workflow/{WORKFLOW_ID}/job",
        {
            "items": [
                {
                    "job_number": UNIT_TEST_JOB_NUMBER,
                    "name": "run-unit-tests-3.9.10",
                    "status": "failed",
                },
                {
                    "job_number": INTEGRATION_TEST_JOB_NUMBER,
                    "name": "run-integration-tests-3.9.10",
                    "status": "failed",
                },
                {
                    "job_number": VALIDATION_JOB_NUMBER,
                    "name": "validate-files",
                    "status": "failed",
                },
                {
                    "job_number": PRE_COMMIT_JOB_NUMBER,
                    "name": "precommit-checks",
                    "status": "success",
                },
            ]
        },
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V1}/project/{PROJECT_SLUG}/{UNIT_TEST_JOB_NUMBER}",
        {
            "steps": [
                {"name": "pytest", "actions": [{"status": "failed", "exit_code": 1}]}
            ]
        },
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V1}/project/{PROJECT_SLUG}/{INTEGRATION_TEST_JOB_NUMBER}",
        {
            "steps": [
                {"name": "pytest", "actions": [{"status": "failed", "exit_code": 1}]}
            ]
        },
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V1}/project/{PROJECT_SLUG}/{VALIDATION_JOB_NUMBER}",
        {
            "steps": [
                {
                    "name": "Test validate files and yaml",
                    "actions": [
                        {
                            "status": "failed",
                            "exit_code": 1,
                            "index": VALIDATION_STEP_AND_INDEX,
                            "step": VALIDATION_STEP_AND_INDEX,
                            "allocation_id": VALIDATION_ALLOCATION_ID,
                        }
                    ],
                }
            ]
        },
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V2}/project/{PROJECT_SLUG}/{UNIT_TEST_JOB_NUMBER}/tests",
        {
            "items": [
                {
                    "name": "test_to_version_no_from_version",
                    "classname": "demisto_sdk.commands.common.content.tests."
                    "objects.pack_objects.abstract_pack_objects.json_content_object_test",
                    "result": "failure",
                },
                {
                    "name": "test_is_file_structure_list[path0--True]",
                    "classname": "demisto_sdk.commands.common.content.tests."
                    "objects.pack_objects.abstract_pack_objects.json_content_object_test",
                    "result": "success",
                },
            ]
        },
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V2}/project/{PROJECT_SLUG}/{INTEGRATION_TEST_JOB_NUMBER}/tests",
        {
            "items": [
                {
                    "name": "test_integration_create_content_artifacts_no_zip",
                    "classname": "demisto_sdk.tests.integration_tests.content_create_artifacts_integration_test",
                    "result": "success",
                },
                {
                    "name": "test_excluded_items_contain_aliased_field",
                    "classname": "demisto_sdk.tests.integration_tests.create_id_set_integration_test.TestCreateIdSet",
                    "result": "failure",
                },
            ]
        },
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V2}/workflow/{WORKFLOW_ID}",
        {"pipeline_num": PIPELINE_NUM},
    ),
    (
        f"{API_BASE_URL}/{CircleCIClient.API_VERSION_V1}/project/{PROJECT_SLUG}/{VALIDATION_JOB_NUMBER}/output/"
        f"{VALIDATION_STEP_AND_INDEX}/{VALIDATION_STEP_AND_INDEX}?file=true&allocation-id={VALIDATION_ALLOCATION_ID}",
        "Packs/ARIAPacketIntelligence/Integrations/ARIAPacketIntelligence/ARIAPacketIntelligence.yml - [IN153]\n"
        "Packs/AccentureCTI/Playbooks/playbook-ACTI_Create_Report-Indicator_Associations.yml - [PB110]\n",
    ),
]


@pytest.fixture(autouse=True)
def mock_circle_ci_data(requests_mock):
    for url, expected_data in CIRCLE_CI_API_MOCKS:
        if isinstance(expected_data, str):
            requests_mock.get(url, text=expected_data)
        else:
            requests_mock.get(url, json=expected_data)


def test_slack_notifier_on_failed_circle_ci_jobs():
    """
    Given -
        circle-ci_utils api mocked responses.

    when -
        constructing a slack message for failed circle-ci_utils jobs.

    Then -
        make sure the correct message with the correct failures is returned even if some of the jobs succeeded.
    """
    from circle_ci_slack_notifier import (
        CircleCIClient,
        CircleCiFailedJobsParser,
        construct_failed_jobs_slack_message,
    )

    parser = CircleCiFailedJobsParser(
        circle_client=CircleCIClient(), workflow_id=WORKFLOW_ID
    )
    assert construct_failed_jobs_slack_message(parser) == [
        {
            "fallback": "Demisto SDK Master-Failure",
            "color": "danger",
            "title": "Demisto SDK Master-Failure",
            "title_link": "https://app.circleci.com/pipelines/github/demisto/demisto-sdk//workflows/1",
            "fields": [
                {
                    "title": "Failed Circle-CI jobs - (3)",
                    "value": "run-unit-tests-3.9.10[pytest]\nrun-integration-tests-3.9.10[pytest]"
                    "\nvalidate-files[Test validate files and yaml]",
                    "short": False,
                },
                {
                    "title": "Failed unit-tests - (1)",
                    "value": "demisto_sdk.commands.common.content.tests.objects.pack_objects.abstract_pack_"
                    "objects.json_content_object_test.test_to_version_no_from_version",
                    "short": False,
                },
                {
                    "title": "Failed integration-tests - (1)",
                    "value": "demisto_sdk.tests.integration_tests.create_id_set_integration_test."
                    "TestCreateIdSet.test_excluded_items_contain_aliased_field",
                    "short": False,
                },
                {
                    "title": "Failed files on validations - (2)",
                    "value": "Packs/ARIAPacketIntelligence/Integrations/ARIAPacketIntelligence/"
                    "ARIAPacketIntelligence.yml - [IN153]\nPacks/AccentureCTI/Playbooks/"
                    "playbook-ACTI_Create_Report-Indicator_Associations.yml - [PB110]",
                    "short": False,
                },
            ],
        }
    ]

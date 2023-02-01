import argparse
import re
from typing import Collection, List, Set, Tuple

from circle_ci_client import API_BASE_URL, PROJECT_SLUG, CircleCIClient
from slack_sdk import WebClient

DEFAULT_SLACK_CHANNEL = "dmst-build"


def options_handler():
    parser = argparse.ArgumentParser(
        description="Parser for circle-ci_utils-slack-notifier args"
    )
    parser.add_argument(
        "-u",
        "--url",
        help="The base URL for the Circle-CI api server",
        default=API_BASE_URL,
    )
    parser.add_argument(
        "-wd",
        "--workflow_id",
        help="The workflow id triggered by the PR",
        required=True,
    )
    parser.add_argument(
        "-st", "--slack_token", help="The token for slack", required=True
    )
    parser.add_argument(
        "-ct", "--circle_token", help="The token for Circle-CI", default=None
    )
    parser.add_argument(
        "-ch",
        "--slack_channel",
        help="The slack channel in which to send the notification",
        default=DEFAULT_SLACK_CHANNEL,
    )
    return parser.parse_args()


class CircleCiFailedJobsParser:
    """
    A class which queries failed jobs of circle CI and parses them.

    Attributes:
        circle_client (CircleCIClient): circle-CI client.
        workflow_id (str): the workflow ID.
        all_failed_jobs (List[dict]): all failed jobs information.
        validation_job_failure_details (dict): details about validation job failure.
    """

    TEST_TYPES = {"unit-tests", "integration-tests"}
    FAILED_JOB_STATUS = "failed"
    FAILED_STEP_STATUS = "failed"
    FAILED_TEST_STATUS = "failure"

    def __init__(self, circle_client: CircleCIClient, workflow_id: str):
        self.circle_client = circle_client
        self.workflow_id = workflow_id
        self.all_failed_jobs = self.circle_client.get_workflow_jobs(self.workflow_id)
        self.validation_job_failure_details = {}  # type: ignore[var-annotated]

    def get_failed_jobs(self) -> List[Tuple[int, str]]:
        """
        Returns a list of failed jobs.

        Returns:
            list[tuple[int, str]]: a list of tuples of job numbers/names for each failed job.
        """
        return [
            (job.job_number, job.name)
            for job in self.all_failed_jobs.items
            if job.status.lower() == self.FAILED_JOB_STATUS
        ]

    def get_failed_job_names_and_steps(self) -> List[str]:
        """
        Returns a list of failed job names and their failed steps.

        Note:
            In case the validation job failed, the validation_job_failure_details will be set in order to
            retrieve later what validations failed.

        Returns:
            list[str]: a list of failed jobs and their steps.
        """
        job_names_and_steps = []
        for job_number, job_name in self.get_failed_jobs():
            job_details = self.circle_client.get_job_details_v1(job_number)
            failed_steps = []
            for job_step in job_details.steps:
                for action in job_step.actions:
                    # if exit code is not None and > 0
                    if (
                        action.status.lower() == self.FAILED_STEP_STATUS
                        and action.exit_code
                    ):
                        failed_steps.append(job_step.name)
                        if (
                            job_step.name == "Test validate files and yaml"
                        ):  # if the validation step failed
                            self.validation_job_failure_details = {
                                "job_number": job_number,
                                "step_number": action.step,
                                "index": action.index,
                                "allocation_id": action.allocation_id,
                            }

            # if the step failed but the circle api does not return on which step it happened, it could happen in case
            # where we have timeouts for example
            job_names_and_steps.append(
                f'{job_name}[{",".join(failed_steps)}]' if failed_steps else job_name
            )
        return job_names_and_steps

    def get_failed_job_numbers_by_test_type(self, test_type: str) -> List[int]:
        """
        Get a list of failed jobs by the test-type which failed (integration test or unit test).

        Args:
            test_type (str): either 'integration-tests' or 'unit-tests'

        Returns:
            list[str]: failed unit job numbers of a specific test type.
        """
        if test_type not in self.TEST_TYPES:
            raise ValueError(
                f'test-type {test_type} must be one of [{",".join(self.TEST_TYPES)}]'
            )

        return [
            job_number
            for job_number, job_name in self.get_failed_jobs()
            if test_type in job_name
        ]

    def get_failed_test_names_by_type(self, test_type: str) -> Set[str]:
        """
        Get the failed tests by a test type, ignores duplications if a test failed in two different jobs which belong
        to the same test type.

        Args:
            test_type (str): either 'integration-tests' or 'unit-tests'

        Returns:
            Set[str]: a set of test names that failed which belong to a specific test type.
        """
        return {
            f"{test}"
            for job_number in self.get_failed_job_numbers_by_test_type(test_type)
            for test in self.get_all_failed_test_names_from_failed_job(job_number)
        }

    def get_failed_unit_tests_names(self) -> Set[str]:
        """
        Get a set of unit-tests names that failed.

        Returns:
            Set[str]: a set of failed unit-tests names.
        """
        return self.get_failed_test_names_by_type(test_type="unit-tests")

    def get_failed_integration_tests(self) -> Set[str]:
        """
        Get a set of integration tests names that failed.

        Returns:
            Set[str]: a set of failed integration tests names.
        """
        return self.get_failed_test_names_by_type(test_type="integration-tests")

    def get_all_failed_test_names_from_failed_job(
        self, failed_job_number: int
    ) -> List[str]:
        """
        Returns a list of all the failed tests names of a specific job number.

        Args:
            failed_job_number (str): a number of a job that failed.

        Returns:
            list[str]: a list of failed test names that failed.
        """
        response = self.circle_client.get_job_test_metadata(failed_job_number)
        return [
            f"{test.classname}.{test.name}"
            for test in response.items
            if test.result.lower() == self.FAILED_TEST_STATUS
        ]

    def get_failed_files_on_validations(self) -> List[str]:
        """
        Get the failed files of the validation errors.

        Returns:
            list[str]: files which failed on validations in case exist.
        """
        if self.validation_job_failure_details:
            response = self.circle_client.get_job_output_file_by_step(
                **self.validation_job_failure_details
            )
            return re.findall(
                pattern=r"Packs\/[/\w-]+\.(?:yml|yaml|json|md|png|xif)\s-\s\[[A-Z]{2}[0-9]{3}\]",
                string=response.text,
            )
        return []

    def get_pipeline_url(self) -> str:
        """
        Get the url for the circle-CI pipeline that failed.

        Returns:
            str: url of the failed circle-CI pipeline.
        """
        workflow_details = self.circle_client.get_workflow_details(self.workflow_id)
        pipeline_number = workflow_details.pipeline_number
        return f"https://app.circleci.com/pipelines/{PROJECT_SLUG}/{pipeline_number}/workflows/{self.workflow_id}"


def construct_failed_jobs_slack_message(parser: CircleCiFailedJobsParser):
    """
    Build up the slack message notifier message in case circle-CI jobs have failed when merging to master.
    """

    def construct_slack_section(_section_title: str, _failed_entities: Collection[str]):
        """
        Construct a single section in the slack body message.

        Args:
            _section_title (str): title of the section.
            _failed_entities (Collection[str]): failed entities such as jobs/tests/validations.

        Returns:
            dict: a format a single section in the slack body message.
        """
        return {
            "title": f"{_section_title} - ({len(_failed_entities)})",
            "value": "\n".join(_failed_entities),
            "short": False,
        }

    slack_body_message = []

    if failed_jobs_names_and_steps := parser.get_failed_job_names_and_steps():
        slack_body_message.append(
            construct_slack_section(
                _section_title="Failed Circle-CI jobs",
                _failed_entities=failed_jobs_names_and_steps,
            )
        )
    else:  # if there aren't any failed jobs
        return slack_body_message

    failed_entities_and_section_names = [
        (parser.get_failed_unit_tests_names(), "Failed unit-tests"),
        (parser.get_failed_integration_tests(), "Failed integration-tests"),
        (parser.get_failed_files_on_validations(), "Failed files on validations"),
    ]

    for failed_entities, section_title in failed_entities_and_section_names:
        if failed_entities:
            slack_body_message.append(
                construct_slack_section(
                    _section_title=section_title, _failed_entities=failed_entities
                )
            )

    title = "Demisto SDK Master-Failure"
    pipeline_url = parser.get_pipeline_url()

    return [
        {
            "fallback": title,
            "color": "danger",
            "title": title,
            "title_link": pipeline_url,
            "fields": slack_body_message,
        }
    ]


def main():
    options = options_handler()
    circle_api_url = options.url
    slack_token = options.slack_token
    circle_ci_token = options.circle_token
    circle_ci_workflow_id = options.workflow_id
    slack_channel = options.slack_channel

    circle_ci_client = CircleCIClient(token=circle_ci_token, base_url=circle_api_url)
    circle_ci_parser = CircleCiFailedJobsParser(
        circle_client=circle_ci_client, workflow_id=circle_ci_workflow_id
    )

    if slack_message := construct_failed_jobs_slack_message(parser=circle_ci_parser):
        slack_client = WebClient(token=slack_token)
        slack_client.chat_postMessage(
            channel=slack_channel,
            attachments=slack_message,
            username="Demisto-SDK CircleCI",
        )


if __name__ == "__main__":
    main()

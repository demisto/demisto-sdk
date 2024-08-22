from pathlib import Path
from typing import Collection, Dict, List, Optional, Set, Tuple

import typer
from github import Github
from github.WorkflowRun import WorkflowRun
from loguru import logger
from slack_sdk import WebClient

from Utils.pytest_junit_parser import JunitParser, TestResult

DEFAULT_SLACK_CHANNEL = "dmst-build-test"


def get_failed_jobs(workflow_run: WorkflowRun) -> List[str]:
    """
    Get a list of failed jobs.

    Args:
        workflow_run: the workflow run object.
    """
    jobs = [job for job in workflow_run.jobs() if job.conclusion == "failure"]

    failed_jobs = []

    for job in jobs:
        failed_steps = []
        for step in job.steps:
            if step.conclusion == "failure":
                failed_steps.append(step.name)

        job_name = job.name
        failed_jobs.append(
            f'{job_name}[{", ".join(failed_steps)}]' if failed_steps else job_name
        )

    return failed_jobs


def get_failed_tests() -> Tuple[List[str], List[str], List[str]]:
    """
    Get all the failed tests from the workflow.

    Args:
        junit_file_paths: paths to all the junit files

    Returns:
        a list of failed unit-tests, a list of failed integration-tests, a list of failed graph-tests.
    """
    failed_unit_tests: Set[TestResult] = set()
    failed_integration_tests: Set[TestResult] = set()
    failed_graph_tests: Set[TestResult] = set()

    for path in Path(".").glob("*/junit.xml"):
        for test_suite in JunitParser(path).test_suites:
            failed_unit_tests = failed_unit_tests.union(set(test_suite.failed_tests))
            failed_integration_tests = failed_integration_tests.union(
                set(test_suite.failed_integration_tests)
            )
            failed_graph_tests = failed_graph_tests.union(
                set(test_suite.failed_graph_tests)
            )

        logger.info(f"Finished processing junit-file {path}")

    return (
        [str(test) for test in failed_unit_tests],
        [str(test) for test in failed_integration_tests],
        [str(test) for test in failed_graph_tests],
    )


def construct_slack_message(
    summary_url: str,
    failed_jobs: List[str],
    failed_tests: Tuple[List[str], List[str], List[str]],
) -> List[Dict]:
    def construct_slack_section(_section_title: str, _failed_entities: Collection[str]):
        """
        Construct a single section in the slack body message.

        Args:
            _section_title (str): title of the section.
            _failed_entities (Collection[str]): failed jobs

        Returns:
            dict: a format a single section in the slack body message.
        """
        return {
            "title": f"{_section_title} - ({len(_failed_entities)})",
            "value": "\n".join(_failed_entities),
            "short": False,
        }

    slack_body_message = []
    if failed_jobs:
        slack_body_message.append(
            construct_slack_section(
                "Failed Github-Actions Jobs",
                _failed_entities=failed_jobs,
            )
        )

    failed_unit_tests, failed_integration_tests, failed_graph_tests = failed_tests

    if failed_unit_tests:
        slack_body_message.append(
            construct_slack_section(
                "Failed Unit Tests", _failed_entities=failed_unit_tests
            )
        )

    if failed_integration_tests:
        slack_body_message.append(
            construct_slack_section(
                "Failed Integration Tests", _failed_entities=failed_integration_tests
            )
        )

    if failed_graph_tests:
        slack_body_message.append(
            construct_slack_section(
                "Failed Graph Tests", _failed_entities=failed_graph_tests
            )
        )

    title = "Demisto SDK Master-Failure"

    if slack_body_message:
        return [
            {
                "fallback": title,
                "color": "danger",
                "title": title,
                "title_link": summary_url,
                "fields": slack_body_message,
            }
        ]
    return []


main = typer.Typer(
    pretty_exceptions_enable=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@main.command()
def slack_notifier(
    ctx: typer.Context,
    workflow_id: int = typer.Option(
        "",
        "--workflow-id",
        help="The workflow id triggered by the PR",
    ),
    slack_token: Optional[str] = typer.Option(
        None,
        "--slack-token",
        help="The token for slack api",
    ),
    github_token: Optional[str] = typer.Option(
        None, "--github-token", "-n", help="The token for Github-Api"
    ),
    slack_channel: str = typer.Option(
        DEFAULT_SLACK_CHANNEL,
        "--slack-channel",
        help="The slack channel to send the summary",
    ),
):
    gh_client = Github(login_or_token=github_token)
    repo = gh_client.get_repo("demisto/demisto-sdk")
    workflow_run: WorkflowRun = repo.get_workflow_run(workflow_id)

    failed_jobs = get_failed_jobs(workflow_run)
    failed_tests = get_failed_tests()
    summary_url = workflow_run.html_url

    slack_message = construct_slack_message(
        summary_url, failed_jobs=failed_jobs, failed_tests=failed_tests
    )
    if slack_message:
        slack_client = WebClient(token=slack_token)
        slack_client.chat_postMessage(
            channel=slack_channel,
            attachments=slack_message,
            username="Demisto-SDK Github-Actions",
        )
        logger.info("Successfully reported failed jobs to slack")
    else:
        logger.info("There are not any failed jobs to report to slack")


if __name__ == "__main__":
    main()

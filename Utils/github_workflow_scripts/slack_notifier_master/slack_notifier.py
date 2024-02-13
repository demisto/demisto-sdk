import argparse
import os
from typing import Collection, Dict, List

from github import Github, WorkflowRun
from slack_sdk import WebClient

from demisto_sdk.commands.common.logger import logger

DEFAULT_SLACK_CHANNEL = "dmst-sdk-slack-notifier-test"


def options_handler():
    parser = argparse.ArgumentParser(
        description="Parser for circle-ci_utils-slack-notifier args"
    )
    parser.add_argument(
        "-wd",
        "--workflow_id",
        help="The workflow id triggered by the PR",
        required=True,
        type=int,
    )
    parser.add_argument(
        "-st", "--slack_token", help="The token for slack", required=True
    )
    parser.add_argument(
        "-ght", "--github_token", help="The token for Github-Api", required=True
    )
    parser.add_argument(
        "-ch",
        "--slack_channel",
        help="The slack channel in which to send the notification",
        default=DEFAULT_SLACK_CHANNEL,
    )
    return parser.parse_args()


def get_failed_jobs(workflow_run: WorkflowRun):
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

    logger.info(f"{failed_jobs=}")
    return failed_jobs


def construct_slack_message(summary_url: str, failed_jobs: List[str]) -> List[Dict]:
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
                _section_title="Failed Github-Actions Jobs",
                _failed_entities=failed_jobs,
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


def main():
    options = options_handler()
    slack_token = options.slack_token
    github_token = options.github_token
    workflow_id = options.workflow_id
    slack_channel = options.slack_channel

    gh_client = Github(login_or_token=github_token)
    repo = gh_client.get_repo("demisto/demisto-sdk")
    workflow_run: WorkflowRun = repo.get_workflow_run(workflow_id)

    failed_jobs = get_failed_jobs(workflow_run)
    summary_url = workflow_run.html_url

    slack_message = construct_slack_message(summary_url, failed_jobs=failed_jobs)
    if slack_message:
        slack_client = WebClient(token=slack_token)
        slack_client.chat_postMessage(
            channel=slack_channel,
            attachments=slack_message,
            username="Demisto-SDK Github-Actions",
        )


if __name__ == "__main__":
    main()

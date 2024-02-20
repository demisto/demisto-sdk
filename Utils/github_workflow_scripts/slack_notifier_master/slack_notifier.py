from typing import Collection, Dict, List, Optional

import typer
from github import Github, WorkflowRun
from slack_sdk import WebClient

DEFAULT_SLACK_CHANNEL = "dmst-build-test"


def get_failed_jobs(workflow_run: WorkflowRun) -> List[str]:
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


main = typer.Typer(pretty_exceptions_enable=False)


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

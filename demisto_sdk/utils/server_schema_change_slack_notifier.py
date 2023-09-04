"""Notify Slack channel SCHEMA_UPDATE_CHANNEL on schema struct file changes.

Schema struct files are those who start with PREFIX and end with SUFFIX."""

import argparse
import os
from pprint import pformat
from typing import Any, Dict, List, Tuple

from slack_sdk import WebClient

from demisto_sdk.commands.common.logger import logger

SCHEMA_UPDATE_CHANNEL = "dmst-schema-change"
GITHUB_BASE_URL = "https://github.com/demisto/server/commit/"
PREFIX = "domain/"
SUFFIX = "_struct.go"


def options_handler():
    parser = argparse.ArgumentParser(
        description="Slack notifier for changes in schema structs."
    )
    parser.add_argument("-c", "--commit", help="The commit hash", required=True)
    parser.add_argument(
        "-s", "--slack_token", help="Token for slack messages", required=True
    )
    options = parser.parse_args()
    return options


def extract_changes_from_commit(commit_hash: str) -> Tuple[str, List[str], dict, str]:
    """Extract relevant changes from git history via commit.

    Args:
        commit_hash: current commit hash

    Return: Tuple of
        commit_github_url: Url of commit on github.
        relevant_changed_files: List of relevant files that were changed.
        change_diffs: Dictionary with changed_files keys and changesets as values.
        commit_author: Author of commit.
    """
    commit_github_url = os.path.join(GITHUB_BASE_URL, commit_hash)
    # Getting Commit Author ('%an') from last (-1) git log entry. Last git log entry is the current commit.
    output_stream = os.popen("git log -1 --pretty=format:'%an'")
    commit_author = output_stream.read()

    # Getting changed file names between last commit on branch (HEAD^) and current commit.
    output_stream = os.popen(
        f"git diff-tree --no-commit-id --name-only -r HEAD^ {commit_hash}"
    )
    changed_files = output_stream.read().split("\n")
    logger.info(f"all Changed files: {changed_files}")

    change_diffs = {}
    for changed_file in changed_files:
        if changed_file.startswith(PREFIX) and changed_file.endswith(SUFFIX):
            # Getting diff of specific changed file from last commit on branch (HEAD^).
            # Filtering only lines indicating changes: starting with + or -
            output_stream = os.popen(
                f"git diff HEAD^ -- {changed_file} | grep '^[+|-][^+|-]'"
            )
            change_diffs[changed_file] = output_stream.read()

    relevant_changed_files = list(change_diffs.keys())
    return commit_github_url, relevant_changed_files, change_diffs, commit_author


def notify_slack(slack_token: str, channel: str, attachments: List[Dict[str, Any]]):
    """Notify slack channel.

    Args:
        slack_token: The token for slack authentication.
        channel: Channel to post the message to.
        attachments: Message to post, formatted as documented in slack_sdk for argument 'attachments'
    """
    slack_client = WebClient(token=slack_token)
    slack_client.chat_postMessage(channel=channel, attachments=attachments)


def build_message(
    commit: str,
    commit_github_url: str,
    changed_files: List[str],
    diffs: dict,
    commit_author: str,
) -> List[Dict[str, Any]]:
    """Construct message for slack.

    Args:
        commit: current commit hash
        commit_github_url: Url of commit on github.
        changed_files: List of relevant files that were changed.
        diffs: Dictionary with changed_files keys and changesets as values.
        commit_author: Author of commit.

    Returns:
        message: slack message in a format like slack_sdk attachment argument expects.
    """

    title = f"Commit {commit[0:7]} Modified Schema Struct Files"
    changes: List[Dict[str, Any]] = [{"value": f"Changed by: {commit_author}"}]
    for changed_file in changed_files:
        changes.append(
            {
                "title": f"{changed_file}",
                "value": f"```{diffs[changed_file]}```",
                "short": False,
            }
        )

    message = [
        {
            "fallback": title,
            "color": "warning",
            "title": title,
            "title_link": commit_github_url,
            "fields": changes,
        }
    ]
    return message


def main():
    try:
        options = options_handler()
        logger.info("Collecting data...")
        (
            commit_github_url,
            changed_files,
            diffs,
            commit_author,
        ) = extract_changes_from_commit(options.commit)
        if len(changed_files) == 0:
            logger.info(
                "Found no relevant schema files in commit. Not sending slack message."
            )
            return
        message = build_message(
            options.commit, commit_github_url, changed_files, diffs, commit_author
        )
        logger.info(f"Posting message...\n{pformat(message)}")
        notify_slack(options.slack_token, SCHEMA_UPDATE_CHANNEL, message)
        logger.info("Notified slack.")

    except Exception as e:
        if "options" in locals() or "options" in globals():
            title = f"Notify Slack on Schema Change failed on Commit {options.commit}"
            message = [
                {
                    "fallback": title,
                    "title_link": os.path.join(GITHUB_BASE_URL, options.commit),
                    "color": "danger",
                    "title": title,
                    "fields": [
                        {
                            "title": f"{type(e)}",
                            "value": f"```{str(e)}```",
                            "short": False,
                        }
                    ],
                }
            ]

            notify_slack(
                slack_token=options.slack_token,
                channel=SCHEMA_UPDATE_CHANNEL,
                attachments=message,
            )
            raise (e)
        else:
            raise (e)


if __name__ == "__main__":
    main()

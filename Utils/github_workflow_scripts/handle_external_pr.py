#!/usr/bin/env python3
import json

import urllib3
from blessings import Terminal
from github import Github

from utils import get_env_var, timestamped_print

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
print = timestamped_print


# Replace the Github Users of the reviewers and security reviewer according to the current contributions team
with open('../../../content/.github/contribution_team.json') as f:
    contribution_team = json.load(f)

SECURITY_REVIEWER = contribution_team['SECURITY_REVIEWER']
REVIEWERS = contribution_team['REVIEWERS']
CONTRIBUTION_TL = contribution_team['CONTRIBUTION_TL']
MARKETPLACE_CONTRIBUTION_PR_AUTHOR = 'xsoar-bot'
WELCOME_MSG = 'Thank you for your contribution. Your generosity and caring are unrivaled! Rest assured - our demisto-sdk ' \
              'wizard @{selected_reviewer} will very shortly look over your proposed changes.'

WELCOME_MSG_WITH_GFORM = 'Thank you for your contribution. Your generosity and caring are unrivaled! Make sure to ' \
                         'register your contribution by filling the [Contribution Registration]' \
                         '(https://forms.gle/XDfxU4E61ZwEESSMA) form, ' \
                         'so our demisto-sdk wizard @{selected_reviewer} will know the proposed changes are ready to be ' \
                         'reviewed.'

CONTRIBUTION_LABEL = 'Contribution'
EXTERNAL_LABEL = "External PR"
SECURITY_LABEL = "Security Review"
SECURITY_CONTENT_ITEMS = [
    "Playbooks",
    "IncidentTypes",
    "IncidentFields",
    "IndicatorTypes",
    "IndicatorFields",
    "Layouts",
    "Classifiers"
]


def is_security_reviewer_required(pr_files: list[str]) -> bool:
    """
    Checks whether a security engineer is needed in the review.

    Arguments:
        - `pr_files`: ``List[str]``: The list of files changed in the Pull Request. Will be used to determine
        whether a security engineer is required for the review.

    Returns: `bool` whether a security engineer should be assigned
    """

    return any(
        item in pr_file
        for pr_file in pr_files
        for item in SECURITY_CONTENT_ITEMS
    )


def main():
    """Handles External PRs (PRs from forks)

    Performs the following operations:
    1. If the external PR's base branch is master we create a new branch and set it as the base branch of the PR.
    2. Labels the PR with the "Contribution" label. (Adds the "Hackathon" label where applicable.)
    3. Assigns a Reviewer.
    4. Creates a welcome comment

    Will use the following env vars:
    - CONTENTBOT_GH_ADMIN_TOKEN: token to use to update the PR
    - EVENT_PAYLOAD: json data from the pull_request event
    """
    terminal = Terminal()

    def cyan(text):
        return f"{terminal.cyan}{text}{terminal.normal}"

    payload_str = get_env_var('EVENT_PAYLOAD')
    if not payload_str:
        raise ValueError('EVENT_PAYLOAD env variable not set or empty')
    payload = json.loads(payload_str)
    print(cyan('Processing PR started'))

    org_name = 'demisto'
    repo_name = 'content'
    gh = Github(get_env_var('CONTENTBOT_GH_ADMIN_TOKEN'), verify=False)
    content_repo = gh.get_repo(f'{org_name}/{repo_name}')

    pr_number = payload.get('pull_request', {}).get('number')
    pr = content_repo.get_pull(pr_number)

    pr_files = [file.filename for file in pr.get_files()]
    print(f'{pr_files=} for {pr_number=}')

    labels_to_add = [CONTRIBUTION_LABEL, EXTERNAL_LABEL]

    # Add the initial labels to PR:
    # - Contribution
    # - External PR
    # - Support Label
    for label in labels_to_add:
        pr.add_to_labels(label)
        print(cyan(f'Added "{label}" label to the PR'))

    # check base branch is master
    if pr.base.ref == 'master':
        print(cyan('Determining name for new base branch'))
        branch_prefix = 'contrib/'
        new_branch_name = f'{branch_prefix}{pr.head.label.replace(":", "_")}'
        existant_branches = content_repo.get_git_matching_refs(f'heads/{branch_prefix}')
        potential_conflicting_branch_names = [branch.ref.removeprefix('refs/heads/') for branch in existant_branches]
        # make sure new branch name does not conflict with existing branch name
        while new_branch_name in potential_conflicting_branch_names:
            # append or increment digit
            if not new_branch_name[-1].isdigit():
                new_branch_name += '-1'
            else:
                digit = str(int(new_branch_name[-1]) + 1)
                new_branch_name = f'{new_branch_name[:-1]}{digit}'
        master_branch_commit_sha = content_repo.get_branch('master').commit.sha
        # create new branch
        print(cyan(f'Creating new branch "{new_branch_name}"'))
        content_repo.create_git_ref(f'refs/heads/{new_branch_name}', master_branch_commit_sha)
        # update base branch of the PR
        pr.edit(base=new_branch_name)
        print(cyan(f'Updated base branch of PR "{pr_number}" to "{new_branch_name}"'))

    # assign reviewers / request review from
    pr.add_to_assignees(CONTRIBUTION_TL)
    reviewers = [CONTRIBUTION_TL]

    # Add a security architect reviewer if the PR contains security content items
    if is_security_reviewer_required(pr_files):
        reviewers.append(SECURITY_REVIEWER)
        pr.add_to_assignees(SECURITY_REVIEWER)
        pr.add_to_labels(SECURITY_LABEL)

    pr.create_review_request(reviewers=reviewers)
    print(cyan(f'Assigned and requested review from "{",".join(reviewers)}" to the PR'))

    # create welcome comment (only users who contributed through Github need to have that contribution form filled)
    message_to_send = WELCOME_MSG if pr.user.login == MARKETPLACE_CONTRIBUTION_PR_AUTHOR else WELCOME_MSG_WITH_GFORM
    body = message_to_send.format(selected_reviewer=CONTRIBUTION_TL)
    pr.create_issue_comment(body)
    print(cyan('Created welcome comment'))


if __name__ == "__main__":
    main()

import os

from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.tools import get_remote_file
from github import Github


CONTENT_ROLES_FILE_PATH = ".github/content_roles.json"


def main():
    content_roles = get_remote_file(
        CONTENT_ROLES_FILE_PATH,
        git_content_config=GitContentConfig(
            repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME,
        ),
    )
    contrib_tl_username = content_roles.get("CONTRIBUTION_TL")
    if not contrib_tl_username:
        raise Exception("contribution TL does not exist in .github/content_roles.json")
    # save the contrib_tl username to a file for a later use in the workflow
    with open("contrib_tl.txt", "w") as f:
        f.write(contrib_tl_username)

    org_name = 'demisto'
    repo_name = 'demisto-sdk'
    gh = Github(os.getenv('GITHUB_TOKEN'), verify=False)
    sdk_repo = gh.get_repo(f'{org_name}/{repo_name}')
    pr_number = os.getenv('PR_NUMBER')
    print(f'{pr_number=}')
    pr = sdk_repo.get_pull(pr_number)
    pr.add_to_assignees(contrib_tl_username)
    pr.add_to_labels('Contribution')
    print('***End of script***')


if __name__ == "__main__":
    main()

import sys

from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.tools import get_remote_file


def main():
    content_roles = get_remote_file(
        ".github/content_roles.json",
        git_content_config=GitContentConfig(
            repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME,
            git_provider=GitProvider.GitHub,
        ),
    )
    contrib_tl_username = content_roles["CONTRIBUTION_TL"]
    if not contrib_tl_username:
        print("No contribution TL")  # noqa: T201
        sys.exit(1)
    # save the contrib_tl username to a file for a later use in the workflow
    print(f"{contrib_tl_username=}")  # noqa: T201
    with open("contrib_tl.txt", "w") as f:
        f.write(contrib_tl_username)


if __name__ == "__main__":
    main()

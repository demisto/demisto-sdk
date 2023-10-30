from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.tools import get_remote_file


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


if __name__ == "__main__":
    main()

import json
import os
import sys
from pathlib import Path

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.tools import get_remote_file


def load_json(file_path: Path) -> dict:
    """Reads and loads json file.

    Args:
        file_path (str): full path to json file.

    Returns:
        dict: loaded json file.

    """
    try:
        if file_path and Path.exists(file_path):
            with open(file_path) as json_file:
                result = json.load(json_file)
        else:
            result = {}
        return result
    except json.decoder.JSONDecodeError:
        return {}


def main():
    content_roles_path = get_remote_file(f"{CONTENT_PATH}/.github/content_roles.json")
    print(content_roles_path)
    content_roles = load_json(content_roles_path)
    print(f'{content_roles=}')
    contrib_tl_username = content_roles["CONTRIBUTION_TL"]
    if not contrib_tl_username:
        print("No contribution TL")  # noqa: T201
        sys.exit(1)
    # save the contrib_tl username to an environment variable to later use in the workflow
    print(f'{contrib_tl_username=}')
    return contrib_tl_username


if __name__ == "__main__":
    main()

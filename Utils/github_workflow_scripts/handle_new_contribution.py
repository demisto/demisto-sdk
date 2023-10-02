import json
import os
import sys
from pathlib import Path

CONTENT_ROOT_PATH = os.path.abspath(
    os.path.join(__file__, "../../../..")
)  # full path to content root repo
CONTENT_ROLES_PATH = Path(
    os.path.join(CONTENT_ROOT_PATH, ".github", "content_roles.json")
)


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
    content_roles = load_json(CONTENT_ROLES_PATH)
    contrib_tl_username = content_roles["CONTRIBUTION_TL"]
    if not contrib_tl_username:
        print("No contribution TL")  # noqa: T201
        sys.exit(1)
    # save the contrib_tl username to an environment variable to later use in the workflow
    return contrib_tl_username


if __name__ == "__main__":
    print(main())

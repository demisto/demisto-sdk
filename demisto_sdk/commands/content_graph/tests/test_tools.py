from pathlib import Path

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yaml, get_json

TEST_DATA_PATH = (
    Path(git_path())
    / "demisto_sdk"
    / "commands"
    / "content_graph"
    / "tests"
    / "test_data"
)


def load_json(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    return get_json(full_path, return_content=True)


def load_yaml(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    return get_yaml(full_path, return_content=True)

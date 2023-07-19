from pathlib import Path

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_file

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
    with open(full_path) as f:
        return json.load(f)


def load_yaml(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    return get_file(full_path, type_of_file='yml', return_content=True)

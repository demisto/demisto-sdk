from pathlib import Path

from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path

TEST_DATA_PATH = (
    Path(git_path())
    / "demisto_sdk"
    / "commands"
    / "content_graph"
    / "tests"
    / "test_data"
)


json = JSON_Handler()
yaml = YAML_Handler()


def load_json(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    with open(full_path, mode="r") as f:
        return json.load(f)


def load_yaml(file_path: str):
    full_path = (TEST_DATA_PATH / file_path).as_posix()
    with open(full_path, mode="r") as f:
        return yaml.load(f)

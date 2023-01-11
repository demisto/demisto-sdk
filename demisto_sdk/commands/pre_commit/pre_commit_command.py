from collections import defaultdict
from dataclasses import dataclass
import os
import subprocess
from packaging.version import Version
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.docker_helper import get_python_version_from_image

yaml = YAML_Handler()

DEFAULT_PYTHON_VERSION = "3.10"

NEEDS_PYVERSION = ["mypy", "pyupgrade"]

PRECOMMIT_TEMPLATE_PATH = Path(__file__).parent / ".pre-commit-config_template.yaml"


PYUPGRADE_MAPPING = {
    "3.10": "py310-plus",
    "3.9": "py39-plus",
    "3.8": "py38-plus",
    "3.7": "py37-plus",
}


with open(PRECOMMIT_TEMPLATE_PATH, "r") as f:
    PRECOMMIT_TEMPLATE = yaml.load(f)


@dataclass
class PreCommit:
    integrations_scripts: Dict[Path, List[Path]]
    files_to_run: Set[Path]

    def __post_init__(self):
        self.hooks = {}
        for repo in PRECOMMIT_TEMPLATE["repos"]:
            for hook in repo["hooks"]:
                self.hooks[hook["id"]] = hook

    @staticmethod
    def handle_mypy(mypy_hook: dict, python_version: str):
        mypy_hook["args"][-1] = f"--python-version={python_version}"

    @staticmethod
    def handle_pyupgrade(pyupgrade_hook: dict, python_version: str):
        pyupgrade_hook["args"][-1] = f"--{PYUPGRADE_MAPPING[python_version]}"

    def run(self, test: bool = False):
        python_version_to_files = defaultdict(set)
        for integration_script, changed_files in self.integrations_scripts.items():
            content_item: Optional[IntegrationScript] = BaseContent.from_path(integration_script)  # type: ignore
            if not content_item:
                print(f"Could not find content item for {integration_script}")
                continue
            python_version = get_python_version_from_image(content_item.docker_image)
            if python_version.startswith("2"):
                continue
            python_version_to_files[python_version].update(changed_files)
        python_version_to_files[DEFAULT_PYTHON_VERSION].update(self.files_to_run)
        for python_version, changed_files in python_version_to_files.items():
            if python_version != DEFAULT_PYTHON_VERSION:
                self.handle_pyupgrade(self.hooks["pyupgrade"], python_version)
                self.handle_mypy(self.hooks["mypy"], python_version)
            with open(CONTENT_PATH / ".pre-commit-config.yaml", "w") as f:
                yaml.dump(PRECOMMIT_TEMPLATE, f)
            print(f"Running pre-commit for {integration_script}")
            env = os.environ.copy()
            if not test:
                env['SKIP'] = "content-test-runner"
            subprocess.run(["pre-commit", "run", "--files", *changed_files], env=env)


def find_hook(hook_name: str):
    for hook in PRECOMMIT_TEMPLATE["repos"]:
        for hook in hook["hooks"]:
            if hook["id"] == hook_name:
                return hook
    raise ValueError(f"Could not find hook {hook_name}")


def pre_commit(
    input_files: Iterable[Path],
    staged=False,
    use_git=False,
    all_files=False,
    test=False,
):
    if not input_files and not use_git and not all_files:
        use_git = True
    if input_files:
        files_to_run = set(input_files)
    elif use_git or staged:
        git_util = GitUtil()
        files_to_run = git_util._get_all_changed_files("origin/master", staged=staged)
    elif all_files:
        files_to_run = set(Path(CONTENT_PATH).rglob("*"))

    categorize_files(files_to_run).run(test)


def categorize_files(files: Set[Path]) -> PreCommit:
    integrations_scripts = defaultdict(list)
    files_to_run = []
    for file in files:
        if {INTEGRATIONS_DIR, SCRIPTS_DIR} & set(file.parts):
            integrations_scripts[file.parent].append(file)
        else:
            files_to_run.append(file)

    return PreCommit(integrations_scripts, files)

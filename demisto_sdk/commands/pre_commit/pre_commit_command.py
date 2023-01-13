from collections import defaultdict
from dataclasses import dataclass
import os
import shutil
import subprocess
import multiprocessing
from packaging.version import Version
import more_itertools
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH

yaml = YAML_Handler()

DEFAULT_PYTHON_VERSION = "3.10"
EMPTY_PYTHON_VERSION = "2.7"

PYTHONPATH = [
    Path(CONTENT_PATH / "Packs" / "Base" / "Scripts" / "CommonServerPython"),
    Path(CONTENT_PATH / "Tests" / "demistomock"),
]

PYTHONPATH.extend(dir for dir in Path(CONTENT_PATH / "Packs" / "ApiModules" / "Scripts").iterdir())

PRECOMMIT_TEMPLATE_PATH = Path(__file__).parent / ".pre-commit-config_template.yaml"

SKIPPED_HOOKS = ("format", "validate")


PYUPGRADE_MAPPING = {
    "3.10": "py310-plus",
    "3.9": "py39-plus",
    "3.8": "py38-plus",
    "3.7": "py37-plus",
}


def python_version_to_pyupgrade(python_version: str):
    return f"py{python_version.replace('.', '')}-plus"


def python_version_to_ruff(python_version: str):
    return f"py{python_version.replace('.', '')}"


with open(PRECOMMIT_TEMPLATE_PATH, "r") as f:
    PRECOMMIT_TEMPLATE = yaml.load(f)


@dataclass
class PreCommit:
    python_version_to_files: Dict[str, Set[Path]]

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
        pyupgrade_hook["args"][-1] = f"--{python_version_to_pyupgrade(python_version)}"

    @staticmethod
    def handle_ruff(ruff_hook: dict, python_version: str):
        ruff_hook["args"][-1] = f"--{python_version_to_ruff(python_version)}"

    @staticmethod
    def handle_pycln(pycln_hook):
        pycln_hook["args"] = [
            f"--skip-imports={','.join(path.name for path in PYTHONPATH)},demisto,CommonServerUserPython"
        ]

    def run(self, test: bool = False, skip_hooks: Optional[List[str]] = None) -> int:
        # handle skipped hooks
        ret_val = 0
        precommit_env = os.environ.copy()
        skipped_hooks = list(SKIPPED_HOOKS)
        skipped_hooks.extend(skip_hooks or [])
        if not test:
            skipped_hooks.append("run-unit-tests")
        precommit_env["SKIP"] = ",".join(skipped_hooks)
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)
        precommit_env["MYPYPATH"] = ":".join(str(path) for path in PYTHONPATH)
        print(f"{precommit_env.get('DOCKER_HOST')=}")
        self.handle_pycln(self.hooks["pycln"])
        for python_version, changed_files in self.python_version_to_files.items():
            print(f"Running pre-commit for {changed_files} with python version {python_version}")
            if python_version.startswith("2"):
                if test:
                    response = subprocess.run(
                        ["pre-commit", "run", "run-unit-test", "--files", *changed_files, "-v"], env=precommit_env
                    )
                    if response.returncode != 0:
                        ret_val = response.returncode
                continue
            if python_version != DEFAULT_PYTHON_VERSION:
                self.handle_pyupgrade(self.hooks["pyupgrade"], python_version)
                self.handle_mypy(self.hooks["mypy"], python_version)
            with open(CONTENT_PATH / ".pre-commit-config.yaml", "w") as f:
                yaml.dump(PRECOMMIT_TEMPLATE, f)
            # use chunks because OS does not support such large comments
            for chunk in more_itertools.chunked_even(changed_files, 10_000):
                response = subprocess.run(["pre-commit", "run", "--files", *chunk, "-v"], env=precommit_env)
                if response.returncode:
                    ret_val = 1
        # remove the config file
        shutil.rmtree(CONTENT_PATH / ".pre-commit-config.yaml", ignore_errors=True)
        return ret_val


def find_hook(hook_name: str):
    for hook in PRECOMMIT_TEMPLATE["repos"]:
        for hook in hook["hooks"]:
            if hook["id"] == hook_name:
                return hook
    raise ValueError(f"Could not find hook {hook_name}")


def pre_commit(
    input_files: Iterable[Path],
    use_git=False,
    staged_only=False,
    all_files=False,
    test=False,
    skip_hooks: Optional[List[str]] = None,
):
    if not any((input_files, staged_only, use_git, all_files)):
        use_git = True
    git_util = GitUtil()
    staged_files = git_util._get_staged_files()
    if input_files:
        files_to_run = set(input_files)
    elif staged_only:
        files_to_run = staged_files
    elif use_git:
        files_to_run = staged_files | git_util._get_all_changed_files("origin/master")
    elif all_files:
        files_to_run = git_util.get_all_files()
    return categorize_files(files_to_run).run(test, skip_hooks)


def categorize_files(files: Set[Path]) -> PreCommit:
    integrations_scripts_mapping = defaultdict(set)
    files_to_run = []
    for file in files:
        if file.is_dir():
            continue
        if set(file.parts) & {INTEGRATIONS_DIR, SCRIPTS_DIR}:
            find_path_index = (i + 1 for i, part in enumerate(file.parts) if part in {INTEGRATIONS_DIR, SCRIPTS_DIR})
            if not find_path_index:
                raise Exception(f"Could not find integration/script path for {file}")
            integration_script_path = Path(*file.parts[: next(find_path_index) + 1])
            integrations_scripts_mapping[integration_script_path].add(file)
        else:
            files_to_run.append(file)

    python_versions_to_files = defaultdict(set)
    with multiprocessing.Pool() as pool:
        integrations_scripts = pool.map(BaseContent.from_path, integrations_scripts_mapping.keys())

    for integration_script in integrations_scripts:
        if not integration_script or not isinstance(integration_script, IntegrationScript):
            continue
        integration_script_path = integration_script.path.parent.relative_to(CONTENT_PATH)
        if python_version := integration_script.python_version:
            version = Version(python_version)
            python_version = f"{version.major}.{version.minor}"
        python_versions_to_files[python_version or EMPTY_PYTHON_VERSION].update(
            integrations_scripts_mapping[integration_script_path] | {integration_script.path}
        )
    python_versions_to_files[DEFAULT_PYTHON_VERSION].update(files_to_run)

    return PreCommit(python_versions_to_files)

from collections import defaultdict
from dataclasses import dataclass
import subprocess
from packaging.version import Version
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import IntegrationScript
import requests
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH

yaml = YAML_Handler()

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
    integrations_scripts_added: Dict[Path, List[Path]]
    integrations_scripts_modified: Dict[Path, List[Path]]
    other_files: Set[Path]
    infra_scripts: Set[Path]

    def run(self):
        for integration_script, changed_files in self.integrations_scripts_modified.items():
            content_item: Optional[IntegrationScript] = BaseContent.from_path(integration_script)  # type: ignore
            if not content_item:
                print(f"Could not find content item for {integration_script}")
                continue
            python_version = get_python_version_from_image(content_item.docker_image)
            pyupgrade = find_hook("pyupgrade")
            pyupgrade["args"][-1] = f"--{PYUPGRADE_MAPPING[python_version]}"

            mypy = find_hook("mypy")
            mypy["args"][-1] = f"--python-version={python_version}"
            with open(CONTENT_PATH / '.pre-commit-config.yaml', "w") as f:
                yaml.dump(PRECOMMIT_TEMPLATE, f)
            subprocess.run(["pre-commit", "run", "--files", *changed_files])


def find_hook(hook_name: str):
    for hook in PRECOMMIT_TEMPLATE["repos"]:
        for hook in hook["hooks"]:
            if hook["id"] == hook_name:
                return hook
    raise ValueError(f"Could not find hook {hook_name}")


def get_python_version_from_image(image: Optional[str]) -> str:
    # check with docker hub the PYTHON_VERSION env var
    if not image:
        return "3.10"
    if ":" not in image:
        repo = image
        tag = "latest"
    else:
        repo, tag = image.split(":")
    response = requests.get(f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull")
    token = response.json()["token"]
    response = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
        headers={
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
            "Authorization": f"Bearer {token}",
        },
    )
    digest = response.json()["config"]["digest"]
    response = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/blobs/{digest}",
        headers={
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
            "Authorization": f"Bearer {token}",
        },
    )
    python_version_envs = [env for env in response.json()["config"]["Env"] if env.startswith("PYTHON_VERSION=")]
    if not python_version_envs:
        return "3.10"
    version = Version(python_version_envs[0].split("=")[1])
    return f"{version.major}.{version.minor}"


def manager():
    # Get all changed integrations and scripts
    git_util = GitUtil()
    prev_ver = "origin/master"
    added_files = git_util.added_files(prev_ver=prev_ver)
    modified_files = git_util.modified_files(prev_ver=prev_ver)
    integrations_scripts_added = defaultdict(list)
    integrations_scripts_modified = defaultdict(list)
    infra_scripts = set()
    other_files = set()
    categorize_files(added_files, integrations_scripts_added, infra_scripts, other_files)
    categorize_files(modified_files, integrations_scripts_modified, infra_scripts, other_files)
    PreCommit(integrations_scripts_added, integrations_scripts_modified, other_files, infra_scripts).run()


def categorize_files(
    files: Set[Path], integrations_scripts: Dict[Path, list], infra_scripts: Set[Path], all_files: Set[Path]
):
    for file in files:
        if {INTEGRATIONS_DIR, SCRIPTS_DIR} & set(file.parts):
            integrations_scripts[file.parent].append(file)
        elif file.suffix == ".py":
            infra_scripts.add(file)
        all_files.add(file)

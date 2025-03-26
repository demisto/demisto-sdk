import itertools
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest

import demisto_sdk.commands.pre_commit.pre_commit_command as pre_commit_command
import demisto_sdk.commands.pre_commit.pre_commit_context as context
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.native_image import NativeImageConfig
from demisto_sdk.commands.pre_commit.hooks.docker import DockerHook
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.system import SystemHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook
from demisto_sdk.commands.pre_commit.pre_commit_command import (
    GitUtil,
    PreCommitContext,
    PreCommitRunner,
    group_by_language,
    pre_commit_manager,
    preprocess_files,
    subprocess,
)
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD

TEST_DATA_PATH = (
    Path(git_path()) / "demisto_sdk" / "commands" / "pre_commit" / "tests" / "test_data"
)

PYTHON_VERSION_TO_FILES = {
    "3.8": {Path("Packs/Pack1/Integrations/integration1/integration1.py")},
    "3.9": {Path("Packs/Pack1/Integrations/integration2/integration2.py")},
    "3.10": {Path("Packs/Pack1/Integrations/integration3/integration3.py")},
}


@pytest.fixture()
def native_image_config(mocker, repo) -> NativeImageConfig:
    native_image_config = NativeImageConfig.from_path(
        repo.docker_native_image_config.path
    )
    mocker.patch.object(
        NativeImageConfig, "get_instance", return_value=native_image_config
    )
    return native_image_config


@dataclass(frozen=True)
class Obj:
    path: Path = Path("somefile")
    object_id: str = "id1"
    is_powershell: bool = False
    docker_image: str = "dockerimage"
    support: str = "xsoar"

    @property
    def docker_images(self):
        return [self.docker_image]


def create_hook(
    hook: dict,
    mode: str = "",
    all_files=False,
    input_files: Optional[List[Path]] = None,
    image_ref: Optional[str] = None,
    docker_image: Optional[str] = None,
):
    """
    This function mocks hook as he returns in _get_hooks() function
    """

    repo_and_hook: dict = {
        "repo": {"repo": "repo", "hooks": [hook]},
        "context": PreCommitContext(
            input_files,
            all_files,
            mode,
            {},
            image_ref=image_ref,
            docker_image=docker_image,
        ),
    }
    repo_and_hook["hook"] = repo_and_hook["repo"]["hooks"][0]
    return repo_and_hook


@dataclass
class MockProcess:
    returncode = 0
    stdout = "finished"
    stderr = ""

    def poll(self):
        return self.returncode

    def wait(self):
        return self.returncode

    def communicate(self):
        return "", ""


def test_config_files(mocker, repo: Repo, native_image_config):
    """
    Given:
        A repository with different scripts and integration of different python versions which require
        split hooks for pylint

    When:
        Calling demisto-sdk pre-commit

    Then:
        - Categorize the scripts and integration by python version,
          and make sure that pre-commit configuration is created
        - make sure split hooks are created properly
        - make sure that the created hooks are pylint based only as its the only hook that should be split
    """

    def devtest_side_effect(
        image_tag: str,
        is_powershell: bool,
        should_pull: bool,
        should_install_mypy_additional_dependencies: bool,
    ):
        return image_tag

    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.docker.devtest_image",
        side_effect=devtest_side_effect,
    )

    mocker.patch.object(
        context,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template-test.yaml",
    )
    pack1 = repo.create_pack("Pack1")
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(repo.path))

    mocker.patch.object(
        pre_commit_command,
        "PRECOMMIT_CONFIG_MAIN_PATH",
        Path(repo.path) / ".pre-commit-config.yaml",
    )
    mocker.patch.object(context, "PRECOMMIT_CONFIG", Path(repo.path) / "config")
    integration1 = pack1.create_integration(
        "integration1", docker_image="demisto/python3:3.9.1.14969"
    )
    integration2 = pack1.create_integration(
        "integration2", docker_image="demisto/python3:3.10.2.14969"
    )
    integration3 = pack1.create_integration(
        "integration3", docker_image="demisto/python3:3.8.2.14969"
    )
    script1 = pack1.create_script("script1", docker_image="demisto/python3:2.7.1.14969")
    integration_deprecated = pack1.create_integration(
        "integration_deprecated", docker_image="demisto/python3:3.10.2.14969"
    )
    integration_deprecated.yml.update({"deprecated": "true"})
    incident_field = pack1.create_incident_field("incident_field")
    classifier = pack1.create_classifier("classifier")
    mocker.patch.object(yaml, "dump", side_effect=lambda *args: [])
    mocker.patch.object(subprocess, "run", return_value=MockProcess())

    relative_paths = {
        path.relative_to(repo.path)
        for path in Path(pack1.path).rglob("*")
        if path.is_file()
    }
    mocker.patch.object(
        GitUtil,
        "get_all_files",
        return_value=relative_paths
        | {Path("README.md"), Path("test.md"), Path("fix.md")},
    )
    files_to_run = preprocess_files([Path(pack1.path)])
    assert files_to_run == relative_paths

    python_version_to_files, _ = group_by_language(files_to_run)
    pre_commit_context = pre_commit_command.PreCommitContext(
        None,
        None,
        None,
        python_version_to_files,
        "",
        pre_commit_template_path=TEST_DATA_PATH
        / ".pre-commit-config_template-test.yaml",
    )
    assert (
        Path(script1.yml.path).relative_to(repo.path)
        in pre_commit_context.python_version_to_files["2.7"]
    )
    assert (
        Path(integration3.yml.path).relative_to(repo.path)
        in pre_commit_context.python_version_to_files["3.8"]
    )
    assert (
        Path(integration1.yml.path).relative_to(repo.path)
        in pre_commit_context.python_version_to_files["3.9"]
    )
    assert (
        Path(integration2.yml.path).relative_to(repo.path)
        in pre_commit_context.python_version_to_files["3.10"]
    )
    assert all(
        Path(obj.path).relative_to(repo.path)
        in pre_commit_context.python_version_to_files["3.10"]
        for obj in (incident_field, classifier)
    )
    assert (
        Path(integration_deprecated.yml.path).relative_to(repo.path)
        not in pre_commit_context.python_version_to_files["3.10"]
    )

    PreCommitRunner.prepare_and_run(pre_commit_context)
    assert (Path(repo.path) / ".pre-commit-config.yaml").exists()


def test_handle_api_modules(mocker, git_repo: Repo):
    """
    Given:
        - A repository with a pack that contains an API module and a pack that contains an integration that uses the API module

    When:
        - Running demisto-sdk pre-commit

    Then:
        - Ensure that the API module is added to the files to run
        - Ensure that the integration that uses the API module is added to the files to run, both related to the *integration*
    """
    pack1 = git_repo.create_pack("ApiModules")
    script = pack1.create_script("TestApiModule")
    pack2 = git_repo.create_pack("Pack2")
    integration = pack2.create_integration(
        "integration1", code="from TestApiModule import *"
    )
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(git_repo.path))
    with ChangeCWD(git_repo.path):
        git_repo.create_graph()
        files_to_run = group_by_language(
            {Path(script.yml.path).relative_to(git_repo.path)}
        )
    files_to_run = {(path, obj.path) for path, obj in files_to_run[0]["2.7"]}
    assert (
        Path(script.yml.path).relative_to(git_repo.path),
        integration.object.path.relative_to(git_repo.path),
    ) in files_to_run
    assert (
        Path(integration.yml.path).relative_to(git_repo.path),
        integration.object.path.relative_to(git_repo.path),
    ) in files_to_run


@pytest.mark.parametrize("github_actions", [True, False])
def test_ruff_hook(github_actions, mocker):
    """
    Testing ruff hook created successfully (the python version is correct and github action created successfully)
    """
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )
    ruff_hook = create_hook(
        {
            "args": ["--fix"],
            "args:nightly": ["--config=nightly_ruff.toml"],
            "id": "ruff",
        }
    )

    mocker.patch.dict(
        os.environ, {"GITHUB_ACTIONS": str(github_actions) if github_actions else ""}
    )
    RuffHook(**ruff_hook).prepare_hook()
    python_version_to_ruff = {"3.8": "py38", "3.9": "py39", "3.10": "py310"}
    for hook, python_version in itertools.zip_longest(
        ruff_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        assert (
            f"--target-version={python_version_to_ruff[python_version]}" in hook["args"]
        )
        assert "--fix" in hook["args"]
        assert hook["name"] == f"ruff-py{python_version}"
        assert hook["files"] == join_files(PYTHON_VERSION_TO_FILES[python_version])
        if github_actions:
            assert hook["args"][2] == "--output-format=github"


def test_ruff_hook_nightly_mode(mocker):
    """
    Testing ruff hook created successfully in nightly mode (the --fix flag is not exist and the --config arg is added)
    """
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )
    ruff_hook = create_hook(
        {
            "args": ["--fix"],
            "args:nightly": ["--config=nightly_ruff.toml"],
            "id": "ruff",
        },
        mode="nightly",
    )

    RuffHook(**ruff_hook).prepare_hook()

    for hook, _ in itertools.zip_longest(
        ruff_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        hook_args = hook["args"]
        assert "--fix" not in hook_args
        assert "--config=nightly_ruff.toml" in hook_args


def test_validate_format_hook_nightly_mode_and_all_files(mocker):
    """
    Testing validate_format hook created successfully (the -a flag is added and the -i arg is not exist)
    """
    validate_format_hook = create_hook(
        {"args": [], "id": "validate"}, mode="nightly", all_files=True
    )
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )

    ValidateFormatHook(**validate_format_hook).prepare_hook()

    hook_args = validate_format_hook["repo"]["hooks"][0]["args"]
    assert "-a" in hook_args
    assert "-i" not in hook_args


def test_validate_format_hook_nightly_mode(mocker):
    """
    Testing validate_format hook created successfully (the -i arg is added and the -a flag is not exist, even in nightly mode)
    """
    validate_format_hook = create_hook(
        {"args": [], "id": "validate"}, mode="nightly", input_files=[Path("file1.py")]
    )
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )

    ValidateFormatHook(**validate_format_hook).prepare_hook()

    hook_args = validate_format_hook["repo"]["hooks"][0]["args"]
    assert "-a" not in hook_args
    assert "-i" in hook_args


def test_validate_format_hook_all_files(mocker):
    """
    Testing validate_format hook created successfully (the -i arg is added and the -a flag is not exist)
    """
    validate_format_hook = create_hook({"args": [], "id": "validate"}, all_files=True)
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )

    ValidateFormatHook(**validate_format_hook).prepare_hook()

    hook_args = validate_format_hook["repo"]["hooks"][0]["args"]
    assert "-a" in hook_args
    assert "-i" not in hook_args


class TestPreprocessFiles:
    def test_preprocess_files_with_input_files(self, mocker):
        input_files = [Path("file1.txt"), Path("file2.txt")]
        expected_output = set(input_files)
        mocker.patch.object(GitUtil, "get_all_files", return_value=set(input_files))
        output = preprocess_files(input_files=input_files)
        assert output == expected_output

    def test_preprocess_files_with_input_yml_files(self, mocker, repo):
        """
        Given:
            - A yml file.
        When:
            - Running demisto-sdk pre-commit -i file1.yml.
        Then:
            - Check that the associated python file was gathered correctly.
        """
        pack1 = repo.create_pack("Pack1")
        mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(repo.path))

        integration = pack1.create_integration("integration")
        relative_paths = {
            path.relative_to(repo.path)
            for path in Path(pack1.path).rglob("*")
            if path.is_file()
        }
        input_files = [Path(integration.yml.path)]
        expected_output = {
            Path(integration.yml.rel_path),
            Path(integration.code.rel_path),
            Path(integration.test.rel_path),
        }
        mocker.patch.object(GitUtil, "get_all_files", return_value=relative_paths)
        output = preprocess_files(input_files=input_files)
        assert output == expected_output

    def test_preprocess_files_with_input_yml_files_not_exists(self, mocker):
        """
        Given:
            - A yml file.
        When:
            - Running demisto-sdk pre-commit -i file1.yml.
        Then:
            - Check that the associated python file was not gathered because it doesn't exist.
        """
        input_files = [Path("file1.yml")]
        expected_output = {Path("file1.yml")}
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(input_files=input_files)
        assert output == expected_output

    def test_preprocess_files_with_staged_only(self, mocker):
        expected_output = set([Path("file1.txt"), Path("file2.txt")])
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=expected_output)
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(staged_only=True)
        assert output == expected_output

    def test_preprocess_files_with_empty_input_files(self):
        input_files = []
        with pytest.raises(ValueError):
            preprocess_files(input_files=input_files)

    def test_preprocess_files_with_nonexistent_files(self, mocker):
        input_files = [Path("file1.txt"), Path("file2.txt"), Path("nonexistent.txt")]
        expected_output = set([Path("file1.txt"), Path("file2.txt")])
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(input_files=input_files)
        assert output == expected_output

    def test_preprocess_files_with_use_git(self, mocker):
        expected_output = set([Path("file1.txt"), Path("file2.txt")])
        mocker.patch.object(
            GitUtil, "_get_all_changed_files", return_value=expected_output
        )
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=set())
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(use_git=True)
        assert output == expected_output

    # Tests that preprocess_files() returns the correct set of Path objects when all_files is True.
    def test_preprocess_files_with_all_files(self, mocker):
        expected_output = set([Path("file1.txt"), Path("file2.txt"), Path("file3.txt")])
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=set())
        output = preprocess_files(all_files=True)
        assert output == expected_output

    @pytest.mark.parametrize(
        "untracked_files, modified_files, untracked_files_in_content ,expected_output",
        [
            (
                ["Packs/untracked.txt"],
                set([Path("Packs/modified.txt")]),
                set([Path("Packs/untracked.txt")]),
                set([Path("Packs/modified.txt"), Path("Packs/untracked.txt")]),
            ),
            (
                [
                    "Packs/untracked_1.txt",
                    "Packs/untracked_2.txt",
                    "invalid/path/untracked.txt",
                    "another/invalid/path/untracked.txt",
                ],
                set([Path("Packs/modified.txt")]),
                set(
                    [
                        Path("Packs/untracked_1.txt"),
                        Path("Packs/untracked_2.txt"),
                    ]
                ),
                set(
                    [
                        Path("Packs/modified.txt"),
                        Path("Packs/untracked_1.txt"),
                        Path("Packs/untracked_2.txt"),
                    ]
                ),
            ),
            (
                [
                    "Packs/untracked_1.txt",
                    "Packs/untracked_2.txt",
                    "invalid/path/untracked.txt",
                    "another/invalid/path/untracked.txt",
                ],
                set(),
                set(
                    [
                        Path("Packs/untracked_1.txt"),
                        Path("Packs/untracked_2.txt"),
                    ]
                ),
                set(
                    [
                        Path("Packs/untracked_1.txt"),
                        Path("Packs/untracked_2.txt"),
                    ]
                ),
            ),
        ],
        ids=[
            "Valid untracked and modified files",
            "Invalid untracked, valid untracked and modified files",
            "No modified files, invalid and valid untracked files only",
        ],
    )
    def test_preprocess_files_in_external_pr_use_case(
        self,
        mocker,
        untracked_files,
        modified_files,
        untracked_files_in_content,
        expected_output,
    ):
        """
        This UT verifies changes made to pre commit command to support collection of
        staged (modified) files when running the build on an external contribution PR.

        Given:
            - A content build is running on external contribution PR, meaning:
                - `CONTRIB_BRANCH` environment variable exists.
                - pre commit command is running in context of an external contribution PR
        When:
            Case 1: All untracked files have a "Pack/..." path, regular modified files are also exist.
            Case 2: Not all untracked files have a "Pack/..." path, irrelevant untracked files also exist which pre commit shouldn't run on.
                    Regular modified files are also exist.
            Case 3: Not all untracked files have a "Pack/..." path, irrelevant untracked files also exist, regular modified files are also exist, No modified files.

        Then:
            - Collect all files within "Packs/" path and run the pre commit on them along with regular modified files if exist.
        """
        mocker.patch.object(
            GitUtil, "_get_all_changed_files", return_value=expected_output
        )
        mocker.patch.dict(os.environ, {"CONTRIB_BRANCH": "true"})
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=modified_files)
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        mocker.patch(
            "git.repo.base.Repo._get_untracked_files",
            return_value=untracked_files,
        )

        output = preprocess_files(use_git=True)
        assert output == expected_output


def test_exclude_hooks_by_version(mocker, repo: Repo):
    """
    Given:
        python_version_to_files with python 2.7 and python 3.8 files
    When:
        Calling exclude hooks by version, to exclude non supported hooks by version
    Then:
        1. python2_files contain the python 2.7 files
        2. python_version_to_files should contain only python 3.8 files
        4. The exclude field of the validate hook should be None
        5. The exclude field of the ruff hook should be file1.py
    """
    mocker.patch.object(
        context,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template-test.yaml",
    )
    mocker.patch.object(context, "CONTENT_PATH", Path(repo.path))
    mocker.patch.object(pre_commit_command, "logger")
    python_version_to_files = {
        "2.7": {(Path("file1.py"), None)},
        "3.8": {(Path("file2.py"), None)},
    }
    pre_commit_context = pre_commit_command.PreCommitContext(
        None,
        None,
        None,
        python_version_to_files,
        "",
        pre_commit_template_path=TEST_DATA_PATH
        / ".pre-commit-config_template-test.yaml",
    )
    PreCommitRunner.prepare_hooks(pre_commit_context)

    hooks = pre_commit_context._get_hooks(pre_commit_context.precommit_template)
    assert hooks["validate"]["hook"].get("exclude") is None
    assert "file1.py" in hooks["ruff"]["hook"]["exclude"]


def test_exclude_hooks_by_support_level(mocker, repo: Repo):
    """
    Given:
        python_version_to_files with python 2.7 and python 3.8 files, 2.7 is xsoar supported in 3.8 is community supported
    When:
        Calling exclude by support level
    Then:
        4. The exclude field of the pycln hook should be None
        5. The exclude field of the autopep should be file2.py
    """
    mocker.patch.object(
        context,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template-test.yaml",
    )
    mocker.patch.object(context, "CONTENT_PATH", Path(repo.path))
    mocker.patch.object(pre_commit_command, "logger")
    python_version_to_files = {
        "2.7": {(Path("file1.py"), Obj())},
        "3.8": {(Path("file2.py"), Obj(support="community"))},
    }
    pre_commit_context = pre_commit_command.PreCommitContext(
        None,
        None,
        None,
        python_version_to_files,
        "",
        pre_commit_template_path=TEST_DATA_PATH
        / ".pre-commit-config_template-test.yaml",
    )

    PreCommitRunner.prepare_hooks(pre_commit_context)

    hooks = pre_commit_context._get_hooks(pre_commit_context.precommit_template)
    assert hooks["pycln"]["hook"].get("exclude") is None
    assert "file2.py" in hooks["autopep8"]["hook"]["exclude"]


args = [
    "-i",
    ".coverage",
    "--report-dir",
    "coverage_report",
    "--report-type",
    "all",
    "--previous-coverage-report-url",
    "https://storage.googleapis.com/marketplace-dist-dev/code-coverage-reports/coverage-min.json",
]
args_nightly = [
    "-i",
    ".coverage",
    "--report-dir",
    "coverage_report",
    "--report-type",
    "all",
    "--allowed-coverage-degradation-percentage",
    "100",
]


@pytest.mark.parametrize(
    "mode, expected_args", [(None, args), ("nightly", args_nightly)]
)
def test_coverage_analyze_general_hook(mode, expected_args):
    """
    Given:
        - A hook and kwargs.
    When:
        - pre-commit command is running.
    Then:
        - Make sure that the coverage-analyze hook was created successfully.
    """

    coverage_analyze_hook = create_hook(
        {"args": args, "args:nightly": args_nightly, "id": "coverage-analyze"},
        mode=mode,
        all_files=True,
        input_files=[Path("file1.py")],
    )
    Hook(**coverage_analyze_hook).prepare_hook()
    hook_args = coverage_analyze_hook["repo"]["hooks"][0]["args"]
    assert expected_args == hook_args


@pytest.mark.parametrize(
    "hook, expected_result",
    [
        (
            {"files": r"\.py$", "exclude": r"_test\.py$", "id": "test"},
            ["file1.py", "file6.py"],
        ),
        (
            {"files": r"\.py$", "id": "test"},
            ["file1.py", "file6.py", "file2_test.py"],
        ),
        (
            {"id": "test"},
            [
                "file1.py",
                "file2_test.py",
                "file3.ps1",
                "file4.md",
                "file5.md",
                "file6.py",
            ],
        ),
        ({"files": r"\.ps1$", "id": "test"}, ["file3.ps1"]),
    ],
)
def test_filter_files_matching_hook_config(hook, expected_result):
    """
    Given:
        an exclude regex, an include regex, and a list of files
    When:
        running filter_files_matching_hook_config on those files
    Then:
        Only get files matching files and not matching exclude

    """
    base_hook = create_hook(hook)

    files = [
        Path(x)
        for x in [
            "file1.py",
            "file2_test.py",
            "file3.ps1",
            "file4.md",
            "file5.md",
            "file6.py",
        ]
    ]

    assert {Path(x) for x in expected_result} == set(
        DockerHook(**base_hook).filter_files_matching_hook_config(files)
    )


def test_skip_hook_with_mode(mocker):
    """
    Given:
        Pre commit template config with skipped hooks

    When:
        Calling pre-commit with nightly mode

    Then:
        Don't generate the skipped hooks
    """

    def get_repos(_pre_commit_config: Dict) -> Dict:
        repos = {}
        for repo in _pre_commit_config["repos"]:
            repos[repo["repo"]] = repo
        return repos

    mocker.patch.object(
        context,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template-test.yaml",
    )
    python_version_to_files = {
        "2.7": {(Path("file1.py"), None)},
        "3.8": {(Path("file2.py"), None)},
    }
    pre_commit_runner = pre_commit_command.PreCommitContext(
        None,
        None,
        "nightly",
        python_version_to_files,
        "",
        pre_commit_template_path=TEST_DATA_PATH
        / ".pre-commit-config_template-test.yaml",
    )
    repos = get_repos(pre_commit_runner.precommit_template)
    assert not repos["https://github.com/charliermarsh/ruff-pre-commit"]["hooks"]
    assert "is-gitlab-changed" not in {
        hook.get("id") for hook in repos["local"]["hooks"]
    }
    assert "should_be_skipped" not in {
        hook.get("id")
        for hook in repos["https://github.com/demisto/demisto-sdk"]["hooks"]
    }


def test_system_hooks():
    """
    Given:
        hook with `system` language

    When:
        running pre-commit command.

    Then:
        The hook entry is updated with the path to the python interpreter that is running.
    """
    import sys

    Path(sys.executable).parent
    system_hook = create_hook(
        {"args": [], "entry": "demisto-sdk", "language": "system", "id": "test"}
    )
    SystemHook(**system_hook).prepare_hook()
    assert (
        system_hook["repo"]["hooks"][0]["entry"]
        == f"{Path(sys.executable).parent}/demisto-sdk"
    )


def test_run_pre_commit_with_json_output_path(mocker, tmp_path):
    """
    Given: A pre-commit setup with a specified JSON output path.
    When: Running the pre-commit manager with a specific hook.
    Then:
        - The exit code is non-zero
        - A JSON output file is created at the specified path
    """
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(tmp_path))

    test_integration_path = (
        tmp_path
        / "Packs"
        / "TestPack"
        / "Integrations"
        / "TestIntegration"
        / "TestIntegration.yml"
    )
    test_integration_path.parent.mkdir(parents=True, exist_ok=True)

    mocker.patch(
        "demisto_sdk.commands.pre_commit.pre_commit_command.preprocess_files",
        return_value=[test_integration_path],
    )

    exit_code = pre_commit_manager(
        input_files=[test_integration_path],
        run_hook="check-ast",
        json_output_path=tmp_path,
    )
    hook_output_path = tmp_path / "check-ast.json"
    assert exit_code != 0
    assert hook_output_path.exists()
    with open(hook_output_path, "r") as f:
        json = JSON_Handler()
        output = json.load(f)
        assert 1 == output.get("returncode")
        assert output.get("stdout").startswith(
            "An error has occurred: FatalError: git failed. Is it installed, and are you in a Git repository directory?"
        )

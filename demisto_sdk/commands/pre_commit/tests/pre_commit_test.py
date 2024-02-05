import itertools
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pytest

import demisto_sdk.commands.pre_commit.pre_commit_command as pre_commit_command
import demisto_sdk.commands.pre_commit.pre_commit_context as context
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.pre_commit.hooks.docker import DockerHook
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.system import SystemHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook
from demisto_sdk.commands.pre_commit.pre_commit_command import (
    GitUtil,
    PreCommitContext,
    PreCommitRunner,
    group_by_language,
    preprocess_files,
    subprocess,
)
from TestSuite.repo import Repo

TEST_DATA_PATH = (
    Path(git_path()) / "demisto_sdk" / "commands" / "pre_commit" / "tests" / "test_data"
)

PYTHON_VERSION_TO_FILES = {
    "3.8": {Path("Packs/Pack1/Integrations/integration1/integration1.py")},
    "3.9": {Path("Packs/Pack1/Integrations/integration2/integration2.py")},
    "3.10": {Path("Packs/Pack1/Integrations/integration3/integration3.py")},
}


@dataclass(frozen=True)
class Obj:
    path: Path = Path("somefile")
    object_id: str = "id1"
    is_powershell: bool = False
    docker_image: str = "dockerimage"
    support_level: str = "xsoar"

    @property
    def docker_images(self):
        return [self.docker_image]


def create_hook(
    hook: dict,
    mode: str = "",
    all_files=False,
    input_files: Optional[List[Path]] = None,
):
    """
    This function mocks hook as he returns in _get_hooks() function
    """

    repo_and_hook: dict = {
        "repo": {"repo": "repo", "hooks": [hook]},
        "context": PreCommitContext(input_files, all_files, mode, {}),
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


def test_config_files(mocker, repo: Repo):
    """
    Given:
        A repository with different scripts and integration of different python versions

    When:
        Calling demisto-sdk pre-commit

    Then:
        Categorize the scripts and integration by python version, and make sure that pre-commit configuration is created for each
    """
    mocker.patch.object(DockerHook, "__init__", return_value=None)
    mocker.patch.object(
        DockerHook,
        "prepare_hook",
        return_value=[{"id": "run-in-docker"}],
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
    mocker.patch.object(
        context,
        "PRECOMMIT_DOCKER_CONFIGS",
        Path(repo.path) / "docker-config",
    )
    mocker.patch.object(
        pre_commit_command,
        "PRECOMMIT_DOCKER_CONFIGS",
        Path(repo.path) / "docker-config",
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
        None, None, None, python_version_to_files, ""
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
    assert list((Path(repo.path) / "docker-config").iterdir())
    assert (Path(repo.path) / ".pre-commit-config-needs.yaml").exists()


def test_mypy_hooks(mocker):
    """
    Testing mypy hook created successfully (the python version is correct)
    """
    mypy_hook = {
        "args": [
            "--ignore-missing-imports",
            "--check-untyped-defs",
            "--show-error-codes",
            "--follow-imports=silent",
            "--allow-redefinition",
            "--python-version=3.10",
        ]
    }
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )

    mypy_hook = create_hook(mypy_hook)
    MypyHook(**mypy_hook).prepare_hook()
    for (hook, python_version) in itertools.zip_longest(
        mypy_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        assert hook["args"][-1] == f"--python-version={python_version}"
        assert hook["name"] == f"mypy-py{python_version}"
        assert hook["files"] == join_files(PYTHON_VERSION_TO_FILES[python_version])


@pytest.mark.parametrize("github_actions", [True, False])
def test_ruff_hook(github_actions, mocker):
    """
    Testing ruff hook created successfully (the python version is correct and github action created successfully)
    """
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )
    ruff_hook = create_hook(
        {"args": ["--fix"], "args:nightly": ["--config=nightly_ruff.toml"]}
    )

    mocker.patch.dict(
        os.environ, {"GITHUB_ACTIONS": str(github_actions) if github_actions else ""}
    )
    RuffHook(**ruff_hook).prepare_hook()
    python_version_to_ruff = {"3.8": "py38", "3.9": "py39", "3.10": "py310"}
    for (hook, python_version) in itertools.zip_longest(
        ruff_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        assert (
            f"--target-version={python_version_to_ruff[python_version]}" in hook["args"]
        )
        assert "--fix" in hook["args"]
        assert hook["name"] == f"ruff-py{python_version}"
        assert hook["files"] == join_files(PYTHON_VERSION_TO_FILES[python_version])
        if github_actions:
            assert hook["args"][2] == "--format=github"


def test_ruff_hook_nightly_mode(mocker):
    """
    Testing ruff hook created successfully in nightly mode (the --fix flag is not exist and the --config arg is added)
    """
    mocker.patch.object(
        PreCommitContext, "python_version_to_files", PYTHON_VERSION_TO_FILES
    )
    ruff_hook = create_hook(
        {"args": ["--fix"], "args:nightly": ["--config=nightly_ruff.toml"]},
        mode="nightly",
    )

    RuffHook(**ruff_hook).prepare_hook()

    for (hook, _) in itertools.zip_longest(
        ruff_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        hook_args = hook["args"]
        assert "--fix" not in hook_args
        assert "--config=nightly_ruff.toml" in hook_args


def test_validate_format_hook_nightly_mode_and_all_files(mocker):
    """
    Testing validate_format hook created successfully (the -a flag is added and the -i arg is not exist)
    """
    validate_format_hook = create_hook({"args": []}, mode="nightly", all_files=True)
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
        {"args": []}, mode="nightly", input_files=[Path("file1.py")]
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
    validate_format_hook = create_hook({"args": []}, all_files=True)
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
        None, None, None, python_version_to_files, ""
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
        "3.8": {(Path("file2.py"), Obj(support_level="community"))},
    }
    pre_commit_context = pre_commit_command.PreCommitContext(
        None, None, None, python_version_to_files, ""
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
        {"args": args, "args:nightly": args_nightly},
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
        ({"files": r"\.py$", "exclude": r"_test\.py$"}, ["file1.py", "file6.py"]),
        (
            {
                "files": r"\.py$",
            },
            ["file1.py", "file6.py", "file2_test.py"],
        ),
        (
            {},
            [
                "file1.py",
                "file2_test.py",
                "file3.ps1",
                "file4.md",
                "file5.md",
                "file6.py",
            ],
        ),
        ({"files": r"\.ps1$"}, ["file3.ps1"]),
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
        None, None, "nightly", python_version_to_files, ""
    )
    repos = pre_commit_runner._get_repos(pre_commit_runner.precommit_template)
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
        {"args": [], "entry": "demisto-sdk", "language": "system"}
    )
    SystemHook(**system_hook).prepare_hook()
    assert (
        system_hook["repo"]["hooks"][0]["entry"]
        == f"{Path(sys.executable).parent}/demisto-sdk"
    )

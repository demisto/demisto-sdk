import itertools
from pathlib import Path

import pytest

import demisto_sdk.commands.pre_commit.pre_commit_command as pre_commit_command
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.pre_commit.hooks.docker import DockerHook
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook
from demisto_sdk.commands.pre_commit.pre_commit_command import (
    PYTHON2_SUPPORTED_HOOKS,
    GitUtil,
    group_by_python_version,
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


def create_hook(hook: dict):
    """
    This function mocks hook as he returns in _get_hooks() function
    """
    repo_and_hook: dict = {"repo": {"repo": "repo", "hooks": [hook]}}
    repo_and_hook["hook"] = repo_and_hook["repo"]["hooks"][0]
    return repo_and_hook


@pytest.mark.parametrize("is_test", [True, False])
def test_config_files(mocker, repo: Repo, is_test: bool):
    """
    Given:
        A repository with different scripts and integration of different python versions

    When:
        Calling demisto-sdk pre-commit

    Then:
        Categorize the scripts and integration by python version, and make sure that pre-commit configuration is created for each
    """
    mocker.patch.object(
        pre_commit_command,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template.yaml",
    )
    pack1 = repo.create_pack("Pack1")
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(repo.path))

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
    mock_subprocess = mocker.patch.object(subprocess, "run")
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

    python_version_to_files, _ = group_by_python_version(files_to_run)
    pre_commit = pre_commit_command.PreCommitRunner(
        None, None, None, python_version_to_files, ""
    )
    assert (
        Path(script1.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["2.7"]
    )
    assert (
        Path(integration3.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.8"]
    )
    assert (
        Path(integration1.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.9"]
    )
    assert (
        Path(integration2.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.10"]
    )
    assert all(
        Path(obj.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.10"]
        for obj in (incident_field, classifier)
    )
    assert (
        Path(integration_deprecated.yml.path).relative_to(repo.path)
        not in pre_commit.python_version_to_files["3.10"]
    )

    pre_commit.run(unit_test=is_test)

    assert mock_subprocess.call_count == 1

    tests_we_should_skip = {"format", "validate", "secrets", "should_be_skipped"}
    if not is_test:
        tests_we_should_skip.add("run-unit-tests")
        tests_we_should_skip.add("coverage-analyze")
        tests_we_should_skip.add("merge-coverage-report")
    for m in mock_subprocess.call_args_list:
        assert set(m.kwargs["env"]["SKIP"].split(",")) == tests_we_should_skip


def test_mypy_hooks():
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
    mypy_hook = create_hook(mypy_hook)

    MypyHook(**mypy_hook).prepare_hook(PYTHON_VERSION_TO_FILES)
    for (hook, python_version) in itertools.zip_longest(
        mypy_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        assert hook["args"][-1] == f"--python-version={python_version}"
        assert hook["name"] == f"mypy-py{python_version}"
        assert hook["files"] == join_files(PYTHON_VERSION_TO_FILES[python_version])


@pytest.mark.parametrize("github_actions", [True, False])
def test_ruff_hook(github_actions):
    """
    Testing ruff hook created successfully (the python version is correct and github action created successfully)
    """
    ruff_hook = create_hook(
        {"args": ["--fix"], "args:nightly": ["--config=nightly_ruff.toml"]}
    )
    RuffHook(**ruff_hook).prepare_hook(PYTHON_VERSION_TO_FILES, github_actions)
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


def test_ruff_hook_nightly_mode():
    """
    Testing ruff hook created successfully in nightly mode (the --fix flag is not exist and the --config arg is added)
    """
    ruff_hook = create_hook(
        {"args": ["--fix"], "args:nightly": ["--config=nightly_ruff.toml"]}
    )
    RuffHook(**ruff_hook, mode="nightly").prepare_hook(PYTHON_VERSION_TO_FILES)

    for (hook, _) in itertools.zip_longest(
        ruff_hook["repo"]["hooks"], PYTHON_VERSION_TO_FILES.keys()
    ):
        hook_args = hook["args"]
        assert "--fix" not in hook_args
        assert "--config=nightly_ruff.toml" in hook_args


def test_validate_format_hook_nightly_mode_and_all_files():
    """
    Testing validate_format hook created successfully (the -a flag is added and the -i arg is not exist)
    """
    validate_format_hook = create_hook({"args": []})
    kwargs = {"mode": "nightly", "all_files": True}
    ValidateFormatHook(**validate_format_hook, **kwargs).prepare_hook(
        PYTHON_VERSION_TO_FILES
    )

    hook_args = validate_format_hook["repo"]["hooks"][0]["args"]
    assert "-a" in hook_args
    assert "-i" not in hook_args


def test_validate_format_hook_nightly_mode():
    """
    Testing validate_format hook created successfully (the -i arg is added and the -a flag is not exist, even in nightly mode)
    """
    validate_format_hook = create_hook({"args": []})
    kwargs = {"mode": "nightly", "input_mode": True}
    ValidateFormatHook(**validate_format_hook, **kwargs).prepare_hook(
        PYTHON_VERSION_TO_FILES
    )

    hook_args = validate_format_hook["repo"]["hooks"][0]["args"]
    assert "-a" not in hook_args
    assert "-i" in hook_args


def test_validate_format_hook_all_files():
    """
    Testing validate_format hook created successfully (the -i arg is added and the -a flag is not exist)
    """
    validate_format_hook = create_hook({"args": []})
    ValidateFormatHook(**validate_format_hook, **{"all_files": True}).prepare_hook(
        PYTHON_VERSION_TO_FILES
    )

    hook_args = validate_format_hook["repo"]["hooks"][0]["args"]
    assert "-a" not in hook_args
    assert "-i" in hook_args


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


def test_exclude_python2_of_non_supported_hooks(mocker, repo: Repo):
    """
    Given:
        python_version_to_files with python 2.7 and python 3.8 files, and unit_test is True
    When:
        Calling handle_python2_files
    Then:
        1. python2_files contain the python 2.7 files
        2. python_version_to_files should contain only python 3.8 files
        3. The logger should print that it is running pre-commit with python 2.7 on file1.py
        4. The exclude field of the run-unit-tests hook should be None
        5. The exclude field of the other hooks should be file1.py
    """
    mocker.patch.object(
        pre_commit_command,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template.yaml",
    )
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(repo.path))
    mocker.patch.object(pre_commit_command, "logger")
    python_version_to_files = {"2.7": {"file1.py"}, "3.8": {"file2.py"}}
    pre_commit_runner = pre_commit_command.PreCommitRunner(
        None, None, None, python_version_to_files, ""
    )

    pre_commit_runner.exclude_python2_of_non_supported_hooks()

    assert (
        "Python 2.7 files running only with the following hooks:"
        in pre_commit_command.logger.info.call_args[0][0]
    )

    for hook in pre_commit_runner.hooks.values():
        if hook["hook"]["id"] in PYTHON2_SUPPORTED_HOOKS:
            assert hook["hook"].get("exclude") is None
        else:
            assert "file1.py" in hook["hook"]["exclude"]


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

    coverage_analyze_hook = create_hook({"args": args, "args:nightly": args_nightly})
    kwargs = {"mode": mode, "all_files": False, "input_mode": True}
    Hook(**coverage_analyze_hook, **kwargs).prepare_hook()
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


def test_no_docker_flag_docker_hook():
    """
    Given:
        run_docker flag (--no-docker) is given.
    When:
        running pre-commit command.
    Then:
        Do not add the docker hook to the list of hooks.
    """
    file_path = Path("SomeFile.py")
    docker_hook = create_hook({"args": ["test"]})
    kwargs = {"mode": None, "all_files": False, "input_mode": True}
    DockerHook(**docker_hook, **kwargs).prepare_hook(
        files_to_run=[file_path], run_docker_hooks=False
    )

    assert len(docker_hook["repo"]["hooks"]) == 0

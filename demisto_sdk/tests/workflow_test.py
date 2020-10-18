import os
import tempfile
import uuid
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Callable, Optional, Tuple

import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from ruamel import yaml
from TestSuite.test_tools import ChangeCWD


def run_command(cmd: str, raise_error: bool = True) -> Tuple[str, str]:
    """
    A simple command runner
    Args:
        cmd: command to run
        raise_error: should raise error (if returncode != 0)

    Returns:
        stdout, stderr
    """
    # reset git lock
    res = Popen(cmd.split(), stderr=PIPE, stdout=PIPE, encoding='utf-8')
    stdout, stderr = res.communicate()
    if raise_error and res.returncode != 0:
        raise SystemExit(f"Error in command \"{cmd}\"\nstdout={stdout}\nsterr={stderr}")
    return stdout, stderr


def run_command_git(cmd: str, raise_error: bool = True) -> Tuple[str, str]:
    run_command('rm -f .git/index.lock')
    if cmd.split()[0] != 'git':
        cmd = 'git' + cmd
    return run_command(cmd, raise_error)


def get_uuid() -> str:
    """
    Gets a uuid
    Returns:
        uuid
    """
    return str(uuid.uuid1())


class ContentGitRepo:
    def __init__(self):
        """
        Will [copy in CircleCI, else will clone] the content to a temp dir.
        """
        # Copy content
        self.branches = []
        circle_content_dir = '/home/circleci/project/content'
        self.tmpdir = tempfile.TemporaryDirectory()
        tmpdir = Path(self.tmpdir.name)
        self.content = tmpdir / 'content'
        # In circleCI, the dir is already there
        if os.path.isdir(circle_content_dir):
            self.content = Path(circle_content_dir)
        # Local machine - search for content alias
        elif os.environ.get('CONTENT'):
            curr_content = os.environ.get('CONTENT')
            run_command(f"cp -r {curr_content} {tmpdir}")
        # Cloning content
        else:
            with ChangeCWD(tmpdir):
                run_command_git("git clone --depth 1 https://github.com/demisto/content.git")
        # Resetting the git branch
        with ChangeCWD(self.content):
            run_command_git("git reset --hard origin/master")
            run_command_git("git clean -f -xd")
            run_command_git("git checkout master")
            run_command_git("git pull")

    def __exit__(self):
        self.tmpdir.cleanup()

    def create_branch(self, branch_name: str = get_uuid(), cwd: Optional[Path] = None) -> str:
        if cwd is None:
            cwd = self.content
        self.branches.append(branch_name)
        run_command_git(f"git checkout -b {branch_name}")
        return branch_name


@pytest.fixture(autouse=True)
def function_setup():
    """
    Cleaning the content repo after every function
    """
    global content_git_repo
    # Function set up
    yield
    # Function teardown - Reset to original repo
    with ChangeCWD(content_git_repo.content):
        run_command_git("git reset --hard origin/master")
        run_command_git("git checkout master")
        for branch in content_git_repo.branches:
            run_command_git(f"git branch -D {branch}", raise_error=False)
        content_git_repo.branches = []


def init_pack(content_repo: ContentGitRepo):
    """
    Given: Instruction to create a new pack using the sdk.
        Fill metadata: y
        Name: Sample
        Description: description
        Pack's type: 1 (xsoar)
        Category: 1 (Analytics & SIEM)
        Create integration: n

    When: Initiating a new pack with the init command

    Then: Validate lint, secrets and validate exit code is 0
    """
    runner = CliRunner(mix_stderr=False)
    with ChangeCWD(content_repo.content):
        content_repo.create_branch()
        try:
            res = runner.invoke(
                main, "init --pack --name Sample",
                input="\n".join(["y", "Sample", "description", "1", "1", "n"])
            )
            assert res.exit_code == 0
            run_command_git("git add .")
            res = runner.invoke(main, "secrets")
            assert res.exit_code == 0
            res = runner.invoke(main, "lint")
            assert res.exit_code == 0
        except AssertionError as e:
            raise AssertionError(f"stdout = {res.stdout}\nstderr = {res.stderr}", e)


def init_integration(content_repo: ContentGitRepo):
    """
    Given: Instruction to create a new integration using the sdk.
        Use ID for as dir name: y

    When: Initiating a new integration with the init command

    Then: Validate lint, secrets and validate exit code is 0
    """
    runner = CliRunner(mix_stderr=False)
    hello_world_path = content_repo.content / "Packs" / "HelloWorld" / "Integrations"
    with ChangeCWD(hello_world_path):
        content_repo.create_branch()
        res = runner.invoke(main, "init --integration -n Sample", input='y')
        assert res.exit_code == 0
        run_command_git("git add .")

    with ChangeCWD(content_repo.content):
        try:
            res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
            assert res.exit_code == 0
            run_command_git("git add .")
            res = runner.invoke(main, "secrets")
            assert res.exit_code == 0
            res = runner.invoke(main, "lint")
            assert res.exit_code == 0
        except AssertionError as e:
            raise AssertionError(f"stdout = {res.stdout}\nstderr = {res.stderr}", e)


def modify_entity(content_repo: ContentGitRepo):
    """
    Given: Modify entity description.

    When: Modifying an entity.

    Then: Validate lint, secrets and validate exit code is 0
    """
    runner = CliRunner(mix_stderr=False)
    with ChangeCWD(content_repo.content / "Packs" / "HelloWorld" / "Scripts" / "HelloWorldScript"):
        content_repo.create_branch()
        # Modify the entity
        script = yaml.safe_load(open("./HelloWorldScript.yml"))
        script['args'][0]["description"] = "new description"
        yaml.safe_dump(script, open("./HelloWorldScript.yml", "w"))
        run_command_git("git add .")
    with ChangeCWD(content_repo.content):
        res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
        assert res.exit_code == 0
        run_command_git("git add .")
        # Get the newest rn file and modify it.
        stdout, stderr = run_command_git("git status")
        lines = stdout.split("\n")
        for line in lines:
            if "ReleaseNotes" in line:
                rn_path = line.split()[-1]
                break
        else:
            raise IndexError(f"Could not find ReleaseNotes in the repo.\n stdout={stdout}\nstderr={stderr}")

        # Replace release notes placeholder
        with open(rn_path) as stream:
            content = stream.read()
            content.replace("%%UPDATE_RN%%", "New rns! Hooray!")
            run_command_git("git add .")
            try:
                res = runner.invoke(main, "secrets")
                assert res.exit_code == 0
                res = runner.invoke(main, "lint")
                assert res.exit_code == 0
            except AssertionError as e:
                raise AssertionError(f"stdout = {res.stdout}\nstderr = {res.stderr}", e)


content_git_repo = ContentGitRepo()


@pytest.mark.parametrize('function', [
    init_pack,
    init_integration,
    modify_entity,
])
def test_sequential_run(function: Callable):
    """
    Pytest will execute tests in parallel. This function ensures the tests will run by sequence.
    Args:
        function: A test to run
    """
    global content_git_repo
    function(content_git_repo)

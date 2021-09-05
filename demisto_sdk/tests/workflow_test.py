import logging
import os
import tempfile
import uuid
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Callable, Generator, Optional, Tuple

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.testing import CliRunner
from ruamel import yaml

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.constants import AUTHOR_IMAGE_FILE_NAME
from TestSuite.test_tools import ChangeCWD


class TestError(BaseException):
    __test__ = False
    pass


def list_files(path: Path) -> Generator[str, None, None]:
    """
    Yield files only in dir
    Args:
        path: Directory to list fies in it

    Yields:
        file name
    """
    for file in os.listdir(path):
        if os.path.isfile(path / file):
            yield file


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
        Will [copy in CircleCI and local machine else will clone] the content to a temp dir.
        """
        # Copy content
        self.branches = []
        circle_content_dir = Path('~/project/content')
        self.tmpdir = tempfile.TemporaryDirectory()
        tmpdir = Path(self.tmpdir.name)
        self.content = tmpdir / 'content'
        logging.debug('Content dir path: %s ' % content_git_repo)
        # In circleCI, the dir is already there
        if os.path.isdir(circle_content_dir):
            logging.debug('Found circle content dir, copying')
            self.run_command(f"cp -r {circle_content_dir} {tmpdir}", cwd=Path(os.getcwd()))
        # # Local machine - search for content alias
        elif os.environ.get('CONTENT'):
            logging.debug('Found CONTENT env var, copying.')
            curr_content = os.environ.get('CONTENT')
            self.run_command(f"cp -r {curr_content} {tmpdir}", cwd=Path(os.getcwd()))
        # # Cloning content
        else:
            logging.debug('Cloning content repo')
            self.run_command("git clone --depth 1 https://github.com/demisto/content.git", cwd=tmpdir)

    def __del__(self):
        """
        Cleanup of the class.
        """
        self.tmpdir.cleanup()

    def create_branch(self, branch_name: str = '') -> str:
        """
        Creates a branch and adding it to the branches lost.

        Returns:
            branch name
        """
        with ChangeCWD(self.content):
            if not branch_name:
                branch_name = get_uuid()
            self.branches.append(branch_name)
            self.run_command(f"git checkout -b {branch_name}")
            return branch_name

    def run_command(self, cmd: str, raise_error: bool = True, cwd: Optional[Path] = None) -> Tuple[str, str]:
        """
        A simple command runner
        Args:
            cmd: command to run
            raise_error: should raise error (if returncode != 0)
            cwd: working dir to run the command. default is self.content

        Returns:
            stdout, stderr
        """
        # reset git lock
        if cwd is None:
            cwd = self.content
        with ChangeCWD(cwd):
            res = Popen(cmd.split(), stderr=PIPE, stdout=PIPE, encoding='utf-8')
            stdout, stderr = res.communicate()
            if raise_error and res.returncode != 0:
                raise SystemExit(f"Error in command \"{cmd}\"\nstdout={stdout}\nsterr={stderr}")
            return stdout, stderr

    def run_validations(self):
        """
        Run all of the following validations:
        * secrets
        * lint -g --no-test
        * validate -g --staged
        * validate -g
        * validate -g --include-untracked
        """
        with ChangeCWD(self.content):
            runner = CliRunner(mix_stderr=False)
            self.run_command("git add .")
            # commit flow - secrets, lint and validate only on staged files without rn
            res = runner.invoke(main, "secrets")
            assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"

            res = runner.invoke(main, "lint -g --no-test")
            assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"

            res = runner.invoke(
                main,
                "validate -g --staged --skip-pack-dependencies --skip-pack-release-notes "
                "--no-docker-checks --debug-git --allow-skipped"
            )

            assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"

            # build flow - validate on all changed files
            res = runner.invoke(main, "validate -g --skip-pack-dependencies --no-docker-checks --debug-git "
                                      "--allow-skipped")
            assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"

            # local run - validation with untracked files
            res = runner.invoke(main, "validate -g --skip-pack-dependencies --no-docker-checks --debug-git -iu "
                                      "--allow-skipped")
            assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"

    def git_cleanup(self):
        """
        Resetting the branch to master and cleaning it.
        """
        with ChangeCWD(self.content):
            self.run_command("git reset --hard origin/master")
            self.run_command("git clean -f -xd")
            self.run_command("git checkout master")
            self.run_command("git pull")

    def update_rn(self, notes: str = "New rns! Hooray!"):
        """
        Will find a single ReleaseNotes file from `git status` and will change
            the placeholder with given notes.

        Args:
            notes: note to replace

        Raises:
            AssertionError if could not find release notes.
        """
        with ChangeCWD(self.content):
            self.run_command("git add .")
            stdout, stderr = self.run_command("git status")
            lines = stdout.split("\n")
            for line in lines:
                if "ReleaseNotes" in line:
                    rn_path = line.split()[-1]
                    break
            else:
                raise IndexError(f"Could not find ReleaseNotes in the repo.\n stdout={stdout}\nstderr={stderr}")
            # Replace release notes placeholder
            with open(rn_path) as stream:
                content = stream.read().replace("%%UPDATE_RN%%", notes)

            with open(rn_path, 'w+') as stream:
                stream.write(content)


content_git_repo: Optional[ContentGitRepo] = None


@pytest.fixture(autouse=True)
def function_setup():
    """
    Cleaning the content repo before every function
    """
    global content_git_repo
    if not content_git_repo:  # lazy initialization. So we don't initialize during test discovery
        content_git_repo = ContentGitRepo()
    # Function setup
    content_git_repo.git_cleanup()
    content_git_repo.create_branch()


def init_pack(content_repo: ContentGitRepo, monkeypatch: MonkeyPatch):
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
    author_image_rel_path = \
        r"test_files/artifacts/content/content_packs/AuthorImageTest/SanityCheck"
    author_image_abs_path = os.path.abspath(f"./{author_image_rel_path}/{AUTHOR_IMAGE_FILE_NAME}")
    monkeypatch.chdir(content_repo.content)
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(
        main, f"init -a {author_image_abs_path} --pack --name Sample",
        input="\n".join(["y", "Sample", "description", "1", "1", "n", "6.0.0"])
    )
    assert res.exit_code == 0, f"Could not run the init command.\nstdout={res.stdout}\nstderr={res.stderr}"
    content_repo.run_validations()


def init_integration(content_repo: ContentGitRepo, monkeypatch: MonkeyPatch):
    """
    Given: Instruction to create a new integration using the sdk.
        Use ID for as dir name: y

    When: Initiating a new integration with the init command

    Then: Validate lint, secrets and validate exit code is 0
    """
    runner = CliRunner(mix_stderr=False)
    hello_world_path = content_repo.content / "Packs" / "HelloWorld" / "Integrations"
    monkeypatch.chdir(hello_world_path)
    res = runner.invoke(main, "init --integration -n Sample", input="\n".join(["y", "6.0.0", "1"]))
    assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"
    content_repo.run_command("git add .")
    monkeypatch.chdir(content_repo.content)
    res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
    assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"
    try:
        content_repo.update_rn()
    except IndexError as exception:
        raise TestError(f"stdout = {res.stdout}\nstderr = {res.stderr}") from exception
    content_repo.run_validations()


def modify_entity(content_repo: ContentGitRepo, monkeypatch: MonkeyPatch):
    """
    Given: Modify entity description.

    When: Modifying an entity.

    Then: Validate lint, secrets and validate exit code is 0
    """
    runner = CliRunner(mix_stderr=False)
    monkeypatch.chdir(content_repo.content / "Packs" / "HelloWorld" / "Scripts" / "HelloWorldScript")
    # Modify the entity
    script = yaml.safe_load(open("./HelloWorldScript.yml"))
    script['args'][0]["description"] = "new description"

    yaml.safe_dump(script, open("./HelloWorldScript.yml", "w"))
    content_repo.run_command("git add .")
    monkeypatch.chdir(content_repo.content)
    res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
    assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"
    content_repo.run_command("git add .")
    # Get the newest rn file and modify it.
    try:
        content_repo.update_rn()
    except IndexError as exception:
        raise TestError(f"stdout = {res.stdout}\nstderr = {res.stderr}") from exception
    content_repo.run_validations()


def all_files_renamed(content_repo: ContentGitRepo, monkeypatch: MonkeyPatch):
    """
    Given: HelloWorld Integration

    When: Renaming the all files to a new name

    Then: Validate lint, secrets and validate exit code is 0
    """
    monkeypatch.chdir(content_git_repo.content)  # type: ignore
    path_to_hello_world_pack = Path("Packs") / "HelloWorld" / "Integrations" / "HelloWorld"
    hello_world_path = content_repo.content / path_to_hello_world_pack
    # rename all files in dir
    for file in list_files(hello_world_path):
        new_file = file.replace('HelloWorld', 'helloworld')
        if not file == new_file:
            content_repo.run_command(
                f"git mv {path_to_hello_world_pack / file} {path_to_hello_world_pack / new_file}"
            )
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
    assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"
    try:
        content_repo.update_rn()
    except IndexError as exception:
        raise TestError(f"stdout = {res.stdout}\nstderr = {res.stderr}") from exception
    content_repo.run_validations()


def rename_incident_field(content_repo: ContentGitRepo, monkeypatch: MonkeyPatch):
    """
    Given: Incident field in HelloWorld pack.

    When: Renaming the entity.

    Then: Validate lint, secrets and validate exit code is 0

    """
    monkeypatch.chdir(content_git_repo.content)  # type: ignore
    hello_world_incidentfields_path = Path("Packs/HelloWorld/IncidentFields/")
    curr_incident_field = hello_world_incidentfields_path / "incidentfield-Hello_World_ID.json"

    content_repo.run_command(
        f"git mv {curr_incident_field} {hello_world_incidentfields_path / 'incidentfield-new.json'}"
    )
    runner = CliRunner(mix_stderr=False)
    res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
    assert res.exit_code == 0, f"stdout = {res.stdout}\nstderr = {res.stderr}"
    try:
        content_repo.update_rn()
    except IndexError as exception:
        raise TestError(f"stdout = {res.stdout}\nstderr = {res.stderr}") from exception
    content_repo.run_validations()


@pytest.mark.parametrize("function", [
    init_pack,
    init_integration,
    modify_entity,
    all_files_renamed,
    rename_incident_field
])
def test_workflow_by_sequence(function: Callable, monkeypatch: MonkeyPatch):
    """
    Pytest will execute tests in parallel. This function ensures the tests will run by sequence.
    Args:
        function: A test to run
        monkeypatch: A pytest's mocker object. Used to change working directory.

    Workflow:
        The tests will use ContentGitRepo as a base content repository.
        Each function will run a different workflow as user should use it.

    Steps:
        Create/Modify files:
            The test will create new files or will modify them.
        Run Demisto-SDK commands:
            Will run any tested demisto-sdk functionality. as the init com
            Will run all validation with expected the test to pass.
            * secrets
            * lint -g --no-test
            * validate -g
    """
    global content_git_repo
    function(content_git_repo, monkeypatch)

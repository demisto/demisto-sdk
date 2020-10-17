import uuid
from subprocess import PIPE, Popen
from typing import Tuple

import git
import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from ruamel import yaml
from TestSuite.test_tools import ChangeCWD


def run_command(cmd: str, stdout=PIPE, stderr=PIPE, encoding='utf-8') -> Tuple[str, str]:
    p = Popen(cmd.split(), stdout=stdout, stderr=stderr, encoding=encoding)
    return p.communicate()


def get_uuid() -> str:
    return str(uuid.uuid1())


class TestWorkflow:
    @pytest.fixture(autouse=True)
    def setup_class(self, tmpdir):
        """
        Will clone the content repo and manage open branches.
        """
        # Copy content
        self.branches = []
        self.content = tmpdir / "content"
        self.repo = git.Git(str(tmpdir))
        self.repo.clone("https://github.com/demisto/content.git", depth=1)

    @pytest.fixture(autouse=True)
    def function_setup(self):
        """
        Cleaning the content repo after every function
        """
        # Here is function buildup
        yield
        # Function teardown - Reset to original repo
        with ChangeCWD(self.content):
            run_command("git reset --hard origin/master")
            run_command("git checkout master")
            for branch in self.branches:
                run_command(f"git branch -D {branch}")
            self.branches = []

    def create_branch(self, branch_name: str = get_uuid()) -> str:
        self.branches.append(branch_name)
        run_command(f"git checkout -b {branch_name}")
        return branch_name

    def test_init_pack(self):
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
        with ChangeCWD(self.content):
            self.create_branch()
            try:
                res = runner.invoke(
                    main, "init --pack --name Sample",
                    input="\n".join(["y", "Sample", "description", "1", "1", "n"])
                )
                assert res.exit_code == 0
                run_command("git add .")
                res = runner.invoke(main, "secrets")
                assert res.exit_code == 0
                res = runner.invoke(main, "lint")
                assert res.exit_code == 0
                res = runner.invoke(main, "validate -g")
                assert res.exit_code == 0
            except AssertionError as e:
                raise AssertionError(f"stdout = {res.stdout}\nstderr = {res.stderr}", e)

    def test_init_integration(self):
        """
        Given: Instruction to create a new integration using the sdk.
            Use ID for as dir name: y

        When: Initiating a new integration with the init command

        Then: Validate lint, secrets and validate exit code is 0
        """
        runner = CliRunner(mix_stderr=False)
        hello_world_path = self.content / "Packs" / "HelloWorld" / "Integrations"
        with ChangeCWD(hello_world_path):
            self.create_branch()
            res = runner.invoke(main, "init --integration -n Sample", input='y')
            assert res.exit_code == 0
            run_command("git add .")

        with ChangeCWD(self.content):
            try:
                res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
                assert res.exit_code == 0
                run_command("git add .")
                res = runner.invoke(main, "validate -g")
                assert res.exit_code == 0
                res = runner.invoke(main, "secrets")
                assert res.exit_code == 0
                res = runner.invoke(main, "lint")
                assert res.exit_code == 0
            except AssertionError as e:
                raise AssertionError(f"stdout = {res.stdout}\nstderr = {res.stderr}", e)

    def test_modify_entity(self):
        """
        Given: Modify entity description.

        When: Modifying an entity.

        Then: Validate lint, secrets and validate exit code is 0
        """
        runner = CliRunner(mix_stderr=False)
        with ChangeCWD(self.content / "Packs" / "HelloWorld" / "Scripts" / "HelloWorldScript"):
            self.create_branch()
            # Modify the entity
            script = yaml.safe_load(open("./HelloWorldScript.yml"))
            script['args'][0]["description"] = "new description"
            yaml.safe_dump(script, open("./HelloWorldScript.yml", "w"))
            run_command("git add .")
        with ChangeCWD(self.content):
            res = runner.invoke(main, "update-release-notes -i Packs/HelloWorld -u revision")
            assert res.exit_code == 0
            run_command("git add .")
            # Get the newest rn file and modify it.
            stdout, stderr = run_command("git status")
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
            run_command("git add .")
            try:
                res = runner.invoke(main, "validate -g")
                assert res.exit_code == 0
                res = runner.invoke(main, "secrets")
                assert res.exit_code == 0
                res = runner.invoke(main, "lint")
                assert res.exit_code == 0
            except AssertionError as e:
                raise AssertionError(f"stdout = {res.stdout}\nstderr = {res.stderr}", e)

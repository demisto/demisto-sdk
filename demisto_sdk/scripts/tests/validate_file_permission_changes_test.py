import os
import stat
from pathlib import Path

import pytest
from git import Blob, Remote
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from demisto_sdk.scripts.scripts_common import CI_ENV_VAR
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestBaseClass:
    from demisto_sdk.scripts.validate_file_permission_changes import main as func

    branch_non_permission = "add-integration-code"
    branch_permission = "set-integration-executable"


class TestValidateFileChangePermissionsLocal(TestBaseClass):

    """
    Test class for validation running in a local environment
    """

    @pytest.fixture(autouse=True)
    def setup(self, git_repo: Repo, mocker: MockerFixture, tmp_path: Path):

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        # Set up 'local' remote
        GitUtil.REPO_CLS.init(str(tmp_path), bare=True)
        git_repo.git_util.repo.delete_remote(Remote(git_repo.git_util.repo, "origin"))
        git_repo.git_util.repo.create_remote("origin", str(tmp_path))

        # Initialize Pack
        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")

    def test_unchanged_permissions(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        no file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - On another branch, we modify the integration by
        adding a code.

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_non_permission)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text("print('some added code')")

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 0

    def test_set_executable(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - On another branch, we modify the integration by
        making the python script executable.

        Then:
        - `validate_file_permission_changes` exit code is 1.
        - The output includes the command how to revert the change.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_permission)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"\x1b[91mFile '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.file_mode)[2:]} to {oct(Blob.executable_mode)[2:]}\x1b[0m"
            in actual_output
        )
        assert (
            f"\x1b[37mPlease revert the file permissions using the command 'chmod -x {py_file_path}'\x1b[0m"
            in actual_output
        )

    def test_set_not_executable(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - The repo includes an executable file. We modify the file to
        be not executable.

        Then:
        - `validate_file_permission_changes` exit code is 1.
        - The output includes the command how to revert the change.
        """

        # Set python file as executable
        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)

        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", cls.branch_permission)

        # Unset python file as executable
        py_file_path.chmod(
            py_file_path.stat().st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH
        )

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"\x1b[91mFile '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.executable_mode)[2:]} to {oct(Blob.file_mode)[2:]}\x1b[0m"
            in actual_output
        )
        assert (
            f"\x1b[37mPlease revert the file permissions using the command 'chmod +x {py_file_path}'\x1b[0m"
            in actual_output
        )


class TestValidateFileChangePermissionsCI(TestBaseClass):
    """
    Test class for validation running in a CI environment.
    """

    @pytest.fixture(autouse=True)
    def setup(self, git_repo: Repo, mocker: MockerFixture, tmp_path: Path):
        """
        Setup method for the class tests.

        - Set CI=true env var.
        - Set content path.
        - Create local remote git repo and add it as remote to content repo.
        - Create a Pack and Integration.
        - Push changes to remote.
        """

        from demisto_sdk.scripts.validate_deleted_files import GitUtil

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        # Set up 'local' remote
        GitUtil.REPO_CLS.init(str(tmp_path), bare=True)
        git_repo.git_util.repo.delete_remote(Remote(git_repo.git_util.repo, "origin"))
        git_repo.git_util.repo.create_remote("origin", str(tmp_path))

        # Initialize Pack
        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.remote().push(refspec="master:master")

    def test_unchanged_permission(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        no file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - The CI env var is set to 'true'.
        - On another branch, we modify the integration by
        adding a code.

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        # Make changes, commit and push to remote
        git_repo.git_util.repo.git.checkout("-b", cls.branch_non_permission)
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")
        git_repo.git_util.repo.remote().push(
            refspec=f"{cls.branch_non_permission}:{cls.branch_non_permission}"
        )

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 0

    def test_unchanged_permission_input_files_supplied(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        no file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - The `--ci` flag is supplied.
        - On another branch, we modify the integration by
        adding a code.
        - The changed files are supplied as input.

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        # Make changes, commit and push to remote
        git_repo.git_util.repo.git.checkout("-b", cls.branch_non_permission)
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")
        git_repo.git_util.repo.remote().push(
            refspec=f"{cls.branch_non_permission}:{cls.branch_non_permission}"
        )

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [py_file_str_path])

        assert result.exit_code == 0

    def test_set_executable(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - On another branch, we modify the integration by
        making the python script executable.

        Then:
        - `validate_file_permission_changes` exit code is 1.
        - The output includes the command how to revert the change.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_permission)
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)
        git_repo.git_util.commit_files(f"Set {py_file_str_path} executable")
        git_repo.git_util.repo.remote().push(
            refspec=f"{cls.branch_permission}:{cls.branch_permission}"
        )

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"\x1b[91mFile '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.file_mode)[2:]} to {oct(Blob.executable_mode)[2:]}\x1b[0m"
            in actual_output
        )
        assert (
            f"\x1b[37mPlease revert the file permissions using the command 'chmod -x {py_file_path}'\x1b[0m"
            in actual_output
        )

    def test_set_not_executable(cls, git_repo: Repo):
        """
        Test `validate_file_permission_changes` exit code when
        file permissions are modified.

        Given:
        - A content repo with a pack and integration.

        When:
        - The repo includes an executable file. We modify the file to
        be not executable.

        Then:
        - `validate_file_permission_changes` exit code is 1.
        - The output includes the command how to revert the change.
        """

        # Set Python file as executable
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)
        git_repo.git_util.commit_files(f"Set {py_file_str_path} executable")
        git_repo.git_util.repo.remote().push(refspec="master:master")

        git_repo.git_util.repo.git.checkout("-b", cls.branch_permission)
        # Unset Python file as executable
        py_file_path.chmod(
            py_file_path.stat().st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH
        )
        git_repo.git_util.commit_files(f"Set {py_file_str_path} not executable")
        git_repo.git_util.repo.remote().push(
            refspec=f"{cls.branch_permission}:{cls.branch_permission}"
        )

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"\x1b[91mFile '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.executable_mode)[2:]} to {oct(Blob.file_mode)[2:]}\x1b[0m"
            in actual_output
        )
        assert (
            f"\x1b[37mPlease revert the file permissions using the command 'chmod +x {py_file_path}'\x1b[0m"
            in actual_output
        )

    def test_unchanged_permission_valid_input_file(cls, git_repo: Repo):
        """
        Test the behavior when we don't change a permission and supply the input file.

        Given:
        - A content repo with a pack and integration.

        When:
        - We add code to a Python file.
        - The changed Python file is supplied as input.

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        # Make changes, commit and push to remote
        git_repo.git_util.repo.git.checkout("-b", cls.branch_non_permission)
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")
        git_repo.git_util.repo.remote().push(
            refspec=f"{cls.branch_non_permission}:{cls.branch_non_permission}"
        )

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [py_file_str_path])

        assert result.exit_code == 0

    def test_invalid_input_files(cls, git_repo: Repo):
        """
        Test the behavior when we don't change a permission and supply the input file.

        Given:
        - A content repo with a pack and integration.

        When:
        - We add code to a Python file.
        - The changed Python file is supplied as invalid input (tuple).

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_non_permission)
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")
        git_repo.git_util.repo.remote().push(
            refspec=f"{cls.branch_non_permission}:{cls.branch_non_permission}"
        )

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [{"some_struct": py_file_str_path}])

        assert result.exit_code == 1

import os
import stat
from pathlib import Path

from git import Blob
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestValidateFileChangePermissions:
    def test_unchanged_permissions(self, git_repo: Repo, mocker: MockerFixture):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", "add-integration-code")

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text("print('some added code')")

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [])

        assert result.exit_code == 0

    def test_set_executable(self, git_repo: Repo, mocker: MockerFixture):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", "set-integration-executable")

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"File '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.file_mode)[2:]} to {oct(Blob.executable_mode)[2:]}"
            in actual_output[1]
        )
        assert (
            f"Please revert the file permissions using the command 'chmod -x {py_file_path}"
            in actual_output[2]
        )

    def test_set_not_executable(self, git_repo: Repo, mocker: MockerFixture):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")

        # Set python file as executable
        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)

        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", "set-integration-not-executable")

        # Unset python file as executable
        py_file_path.chmod(
            py_file_path.stat().st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH
        )

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"File '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.executable_mode)[2:]} to {oct(Blob.file_mode)[2:]}"
            in actual_output[1]
        )
        assert (
            f"Please revert the file permissions using the command 'chmod +x {py_file_path}"
            in actual_output[2]
        )

import os
import stat
from pathlib import Path

import pytest
import typer
from git import Blob
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from demisto_sdk.scripts.validate_file_permission_changes import (
    CI_ENV_VAR,
    ERROR_IS_CI_INVALID,
    is_ci,
)
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestValidateFileChangePermissionsLocal:
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
            f"\x1b[91mFile '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.file_mode)[2:]} to {oct(Blob.executable_mode)[2:]}\x1b[0m"
            in actual_output
        )
        assert (
            f"\x1b[37mPlease revert the file permissions using the command 'chmod -x {py_file_path}'\x1b[0m"
            in actual_output
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
            f"\x1b[91mFile '{py_file_path.relative_to(git_repo.path)}' permission was changed from {oct(Blob.executable_mode)[2:]} to {oct(Blob.file_mode)[2:]}\x1b[0m"
            in actual_output
        )
        assert (
            f"\x1b[37mPlease revert the file permissions using the command 'chmod +x {py_file_path}'\x1b[0m"
            in actual_output
        )

    def test_set_executable_not_pack(self, git_repo: Repo, mocker: MockerFixture):
        """
        Test a scenario where we modify a file's permission
        outside the Packs directory.

        Given:
        - A content repo with a pack and integration.

        When:
        - We add a new file outside the Packs directory.
        - We then modify the file permissions to make it executable.

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        pass


class TestValidateFileChangePermissionsCI:
    """
    Test class for validation running in a CI environment.
    """

    def test_unchanged_permission(self, git_repo: Repo, mocker: MockerFixture):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")

        git_repo.git_util.repo.git.checkout("-b", "add-integration-code")
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [])

        assert result.exit_code == 0

    def test_unchanged_permission_input_files_supplied(
        self, git_repo: Repo, mocker: MockerFixture
    ):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", "add-integration-code")

        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [py_file_str_path])

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
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", "set-integration-executable")

        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)
        git_repo.git_util.commit_files(f"Set {py_file_str_path} executable")

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [])

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
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")

        # Set python file as executable
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.chmod(py_file_path.stat().st_mode | stat.S_IEXEC)

        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.git.checkout("-b", "set-integration-not-executable")

        # Unset python file as executable
        py_file_path.chmod(
            py_file_path.stat().st_mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH
        )
        git_repo.git_util.commit_files(f"Set {py_file_str_path} not executable")

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [])

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

    def test_unchanged_permission_valid_input_file(
        self, git_repo: Repo, mocker: MockerFixture
    ):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")

        git_repo.git_util.repo.git.checkout("-b", "add-integration-code")
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [py_file_str_path])

        assert result.exit_code == 0

    def test_invalid_input_files(self, git_repo: Repo, mocker: MockerFixture):
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

        from demisto_sdk.commands.common.git_util import Repo as GitRepo
        from demisto_sdk.scripts.validate_deleted_files import GitUtil
        from demisto_sdk.scripts.validate_file_permission_changes import main

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.dict(os.environ, {CI_ENV_VAR: "true"})
        mocker.patch.object(GitRepo, "remote", return_value="")
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")

        git_repo.git_util.repo.git.checkout("-b", "add-integration-code")
        py_file_str_path = git_repo.packs[0].integrations[0].code.path
        py_file_path = Path(py_file_str_path)
        py_file_path.write_text("print('some added code')")
        git_repo.git_util.commit_files("Added some code")

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(main, [{"some_struct": py_file_str_path}])

        assert result.exit_code == 1


class TestIsCI:

    valid_true = "true"
    valid_false = "false"
    invalid_false = "fale"

    def test_flag_true_supplied(self):
        """
        Given:
        - The `--ci` flag is supplied.

        When:
        - The `--ci` flag supplied is `True`.

        Then:
        - `is_ci` returns `True`
        """

        actual = is_ci(flag=True)

        assert actual

    def test_flag_false_supplied(self):
        """
        Given:
        - The `--ci` flag is supplied.

        When:
        - The `--ci` flag supplied is `False`.

        Then:
        - `is_ci` returns `False`
        """

        actual = is_ci(flag=False)

        assert not actual

    def test_flag_not_supplied_valid_true_env_var_supplied(self, mocker: MockerFixture):
        """
        Given:
        - No `--ci` flag is not supplied.

        When:
        - The `CI` environmental variable is set to 'true'.

        Then:
        - `is_ci` returns `True`
        """

        mocker.patch.dict(os.environ, {CI_ENV_VAR: self.valid_true})

        actual = is_ci()

        assert actual

    def test_flag_not_supplied_valid_false_env_var_supplied(
        self, mocker: MockerFixture
    ):
        """
        Given:
        - No `--ci` flag is not supplied.

        When:
        - The `CI` environmental variable is set to 'false'.

        Then:
        - `is_ci` returns `False`
        """

        mocker.patch.dict(os.environ, {CI_ENV_VAR: self.valid_false})

        actual = is_ci()

        assert not actual

    def test_flag_not_supplied_invalid_env_var_supplied(self, mocker: MockerFixture):
        """
        Given:
        - No `--ci` flag is not supplied.

        When:
        - The `CI` environmental variable is set to an invalid value 'fale'.

        Then:
        - `typer.BadParameter` is raised.
        """

        mocker.patch.dict(os.environ, {CI_ENV_VAR: self.invalid_false})

        with pytest.raises(typer.BadParameter) as exception_info:
            is_ci()

        assert str(exception_info.value) == ERROR_IS_CI_INVALID.format(
            env_var_str=self.invalid_false
        )

    def test_flag_not_supplied_env_var_not_supplied(self):
        """
        Given:
        - No `--ci` flag is not supplied.

        When:
        - The `CI` environmental variable is not set.

        Then:
        - `False` is returned.
        """

        actual = is_ci()

        assert not actual

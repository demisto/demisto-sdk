import stat
from pathlib import Path

from typer.testing import CliRunner


class TestValidateFileChangePermissions:

    """
    Test class for validation running in a local environment
    """

    from demisto_sdk.scripts.validate_file_permission_changes import main as func

    # branch_non_permission = "add-integration-code"
    # branch_permission = "set-integration-executable"

    # @pytest.fixture(autouse=True)
    # def setup(self, git_repo: Repo, mocker: MockerFixture, tmp_path: Path):

    #     from demisto_sdk.commands.common.git_util import Repo as GitRepo
    #     from demisto_sdk.scripts.validate_deleted_files import GitUtil

    #     mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
    #     mocker.patch.object(GitRepo, "remote", return_value="")
    #     mocker.patch.object(GitUtil, "fetch", return_value=None)

    #     # Set up 'local' remote
    #     GitUtil.REPO_CLS.init(str(tmp_path), bare=True)
    #     git_repo.git_util.repo.delete_remote(Remote(git_repo.git_util.repo, "origin"))
    #     git_repo.git_util.repo.create_remote("origin", str(tmp_path))

    #     # Initialize Pack
    #     git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
    #     git_repo.git_util.commit_files("Added a new Pack and Integration")

    def test_unchanged_permissions(cls, tmp_path: Path):
        """
        Test `validate_file_permission_changes` exit code when
        no the executable bits aren't set.

        Given:
        - A temporary directory.

        When:
        - A new file is created.

        Then:
        - `validate_file_permission_changes` exit code is 0.
        """

        file = tmp_path / "a"
        file.write_text("print('some added code')")

        runner = CliRunner()

        result = runner.invoke(cls.func, [str(file)])

        assert result.exit_code == 0

    def test_set_executable(cls, tmp_path: Path):
        """
        Test `validate_file_permission_changes` exit code when
        no the executable bits aren't set.

        Given:
        - A temporary directory.

        When:
        - A new file is created and executable bit is set.

        Then:
        - `validate_file_permission_changes` exit code is 1.
        """

        file = tmp_path / "a"
        file.write_text("print('some added code')")
        file.chmod(file.stat().st_mode | stat.S_IEXEC)

        runner = CliRunner()

        result = runner.invoke(cls.func, [str(file)])

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"\x1b[91mFile '{file}' has executable bits set. Please revert using command 'chmod -x {file}'\x1b[0m"
            in actual_output
        )

    def test_one_executable_one_not(cls, tmp_path: Path):
        """
        Test `validate_file_permission_changes` exit code when
        two files are fed in.

        Given:
        - A temporary directory.

        When:
        - A new file is created.
        - A new file is created and executable bit is set.

        Then:
        - `validate_file_permission_changes` exit code is 1.
        """

        not_executable_file = tmp_path / "not_executable"
        not_executable_file.write_text("print('some added code')")

        executable_file = tmp_path / "executable"
        executable_file.write_text("print('some added code')")
        executable_file.chmod(executable_file.stat().st_mode | stat.S_IEXEC)

        runner = CliRunner()

        result = runner.invoke(
            cls.func, [str(not_executable_file), str(executable_file)]
        )

        assert result.exit_code == 1
        actual_output = result.stdout.splitlines()
        assert actual_output
        assert (
            f"\x1b[91mFile '{executable_file}' has executable bits set. Please revert using command 'chmod -x {executable_file}'\x1b[0m"
            in actual_output
        )

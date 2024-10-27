import stat
from pathlib import Path

from typer.testing import CliRunner


class TestValidateFileChangePermissions:
    """
    Test class for validation running in a local environment
    """

    from demisto_sdk.scripts.validate_file_permission_changes import main as func

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
        assert (
            f"File '{file}' has executable bits set. Please revert using command 'chmod -x {file}'"
            in result.stdout
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
        assert (
            f"File '{executable_file}' has executable bits set. Please revert using command 'chmod -x {executable_file}'"
            in result.stdout
        )

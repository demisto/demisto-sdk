import os
from pathlib import Path

import pytest
from git import Remote
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestBaseClass:
    from demisto_sdk.scripts.validate_mypy_global_ignore import main as func

    remote = "origin"

    branch_no_mypy_ignore = "add-integration-code"
    added_code = "print('some added code')"

    branch_add_mypy_ignore = "add-mypy-ignore"
    added_mypy_ignore = f"{added_code}  # type: ignore"
    added_mypy_ignore_tab = "\t# type: ignore"

    branch_add_mypy_global_ignore = "add-mypy-global-ignore"
    added_mypy_global_ignore = "# type: ignore"
    added_mypy_global_ignore_1 = "#type: ignore"
    added_mypy_global_ignore_2 = "# type:ignore"
    added_mypy_global_ignore_3 = "#type:ignore"


class TestValidateMyPyGlobalIgnoreLocal(TestBaseClass):

    """
    Test class for validation of mypy global ignore in local
    context
    """

    @pytest.fixture(autouse=True)
    def setup(self, git_repo: Repo, mocker: MockerFixture, tmp_path: Path):

        from demisto_sdk.scripts.validate_deleted_files import GitUtil

        mocker.patch.dict(os.environ, {"DEMISTO_SDK_CONTENT_PATH": git_repo.path})
        mocker.patch.object(GitUtil, "fetch", return_value=None)

        # Set up 'local' remote
        GitUtil.REPO_CLS.init(str(tmp_path), bare=True)
        git_repo.git_util.repo.delete_remote(Remote(git_repo.git_util.repo, "origin"))
        git_repo.git_util.repo.create_remote("origin", str(tmp_path))

        # Initialize Pack
        git_repo.create_pack(name="TestPack").create_integration(name="TestIntegration")
        git_repo.git_util.commit_files("Added a new Pack and Integration")
        git_repo.git_util.repo.remote().push(refspec="master:master")

    def test_mypy_ignore_not_added(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        non-mypy ignore comment is added.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Valid Python code is added to the intengration code.

        Then:
        - Exit code 0 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_code)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 0

    def test_mypy_ignore_add_not_global(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        a non-global mypy ignore comment is added to the end
        of a statement.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Type ignore comment is added to the end of a print
        statement.

        Then:
        - Exit code 0 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_mypy_ignore)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 0

    def test_mypy_ignore_add_tab(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        a non-global mypy ignore comment is added in the beginning
        of the statement with a tab.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Type ignore comment is added after a tab.

        Then:
        - Exit code 0 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_mypy_ignore_tab)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 0

    def test_mypy_ignore_add_global(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        a global mypy ignore comment is added.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_global_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_mypy_global_ignore)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1

    def test_mypy_ignore_add_global_no_whitespace_1(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        a global mypy ignore comment is added with not whitespace
        between '#' and 'type'.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_global_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_mypy_global_ignore_1)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1

    def test_mypy_ignore_add_global_no_whitespace_2(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        a global mypy ignore comment is added with not whitespace
        between ':' and 'ignore'.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_global_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_mypy_global_ignore_2)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1

    def test_mypy_ignore_add_global_no_whitespace_3(cls, git_repo: Repo):
        """
        Test the behavior of `validate_mypy_global_ignore` when
        a global mypy ignore comment is added with not whitespace
        in the ignore comment.

        Given:
        - A content git repo with an integration pushed to remote.
        - A feature branch.

        When:
        - Type ignore comment is added globally.

        Then:
        - Exit code 1 is returned.
        """

        git_repo.git_util.repo.git.checkout("-b", cls.branch_add_mypy_global_ignore)

        py_file_path = Path(git_repo.packs[0].integrations[0].code.path)
        py_file_path.write_text(cls.added_mypy_global_ignore_3)

        git_repo.git_util.stage_file(py_file_path)

        runner = CliRunner()

        with ChangeCWD(git_repo.path):
            result = runner.invoke(cls.func, [])

        assert result.exit_code == 1


class TestValidateMyPyGlobalIgnoreCI(TestBaseClass):

    """
    Test class for validation of mypy global ignore in CI
    context
    """

import pytest

from demisto_sdk.commands.lint.linter import Linter
from demisto_sdk.commands.common.git_tools import git_path


class TestLinter:
    DIR_LIST = [
        f"{git_path()}/demisto_sdk/tests/test_files/fake_integration"
    ]

    @pytest.mark.parametrize("directory", DIR_LIST)
    def test_get_common_server_python(self, directory):
        linter = Linter(directory)
        ans = linter.get_common_server_python()
        linter.remove_common_server_python()
        assert ans

    @pytest.mark.skip(reason="No mypy")
    @pytest.mark.parametrize("directory", DIR_LIST)
    def test_run_mypy(self, directory):
        linter = Linter(directory)
        linter.run_mypy("2.7")

    @pytest.mark.parametrize("directory", DIR_LIST)
    def test_run_bandit(self, directory):
        linter = Linter(directory)
        linter.run_bandit(3.7)

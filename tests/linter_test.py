import os
import pytest

from demisto_sdk.dev_tools.linter import Linter


class TestLinter:

    DIR_LIST = [
        "tests/test_files/fake_integration"
    ]
    @pytest.mark.parametrize("directory", DIR_LIST)
    def test_get_common_server_python(self, directory):
        linter = Linter(directory)
        ans = linter._get_common_server_python()
        linter.remove_common_server_python()
        assert ans

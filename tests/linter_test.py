import os

from demisto_sdk.dev_tools.linter import Linter


class TestLinter:
    path = "./CommonServerPython.py"

    def setup_class(self):
        if os.path.isfile(self.path):
            os.remove(self.path)

    def test_get_common_server_python(self):
        Linter._get_common_server_python()
        assert os.path.isfile(self.path)

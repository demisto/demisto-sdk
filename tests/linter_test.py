import os
from shutil import copyfile

from demisto_sdk.dev_tools.linter import Linter


class TestLinter:
    path = "./CommonServerPython.py"
    path_to_move = "./CommonServerPython_COPY.py"
    is_file_copied = False

    @classmethod
    def setup_class(cls):
        if os.path.isfile(cls.path):
            copyfile(cls.path, cls.path_to_move)
            cls.is_file_copied = True
            os.remove(cls.path)

    @classmethod
    def teardown_class(cls):
        if cls.is_file_copied:
            os.remove(cls.path)
            copyfile(cls.path_to_move, cls.path)
            os.remove(cls.path_to_move)
        else:
            os.remove(cls.path)

    def test_get_common_server_python(self):
        Linter._get_common_server_python()
        assert os.path.isfile(self.path)

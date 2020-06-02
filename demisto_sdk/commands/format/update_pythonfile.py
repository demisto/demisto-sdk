from typing import Tuple
import subprocess

from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_VALIDATE_PY_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdate
from demisto_sdk.commands.common.tools import LOG_COLORS, print_color


BLACK_INTERNAL_ERROR = 123


class PythonFileFormat(BaseUpdate):
    """PythonFileFormat class is designed to update python file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the python file to.
    """

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = ''
                 , no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)
        self.no_validate = True

    def is_format_by_black(self, py_file_path):
        """Run black formatter on python file.
        Args:
            py_file_path (str): The python file path.
        Returns:
            bool. True if succeed to run black on file, False otherwise.
        """
        print("\nRunning black on file: {}\n".format(py_file_path))
        try:
            if subprocess.call(["black", "--skip-string-normalization", "-v", "--line-length", "120", py_file_path])\
                    == BLACK_INTERNAL_ERROR:
                return False
            return True
        except FileNotFoundError:
            return "black skipped! It doesn't seem you have black installed.\n " \
                   "Make sure to install it with: pip install black.\n " \
                   "Then run: black {}".format(py_file_path)

    def run_format(self) -> int:
        print_color(F'\n=======Starting updates for file: {self.source_file}=======', LOG_COLORS.WHITE)

        is_black_passed = self.is_format_by_black(str(self.source_file))
        if is_black_passed:
            print_color(F'=======Finished updates for files: {self.output_file}=======\n', LOG_COLORS.WHITE)
            return SUCCESS_RETURN_CODE
        return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration python updater."""
        format = self.run_format()
        return format, SKIP_VALIDATE_PY_RETURN_CODE


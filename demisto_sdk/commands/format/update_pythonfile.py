import subprocess
from typing import Tuple

from demisto_sdk.commands.common.tools import LOG_COLORS, print_color
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE, SKIP_VALIDATE_PY_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdate

BLACK_INTERNAL_ERROR = 123


class PythonFileFormat(BaseUpdate):
    """PythonFileFormat class is designed to update python file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the python file to.

    """

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = True):
        super().__init__(input, output, path, from_version, no_validate)

    def format_py_using_autopep(self, py_file_path):
        """Run autopep8 formatter on python file.
        Args:
            py_file_path (str): The python file path.
        Returns:
            bool. True if succeed to run autopep8 on file, False otherwise.
        """
        print("\nRunning autopep8 on file: {}\n".format(py_file_path))
        try:
            if subprocess.call(["autopep8", "-i", "--max-line-length", "130", py_file_path]) \
                    == BLACK_INTERNAL_ERROR:
                return False
            return True
        except FileNotFoundError:
            print_color("autopep8 skipped! It doesn't seem you have autopep8 installed.\n "
                        "Make sure to install it with: pip install autopep8.\n "
                        "Then run: autopep8 -i {}".format(py_file_path), LOG_COLORS.YELLOW)
            return False

    def run_format(self) -> int:
        print_color(F'\n=======Starting updates for file: {self.source_file}=======', LOG_COLORS.WHITE)

        is_autopep_passed = self.format_py_using_autopep(str(self.source_file))
        if is_autopep_passed:
            print_color(F'=======Finished updates for files: {self.output_file}=======\n', LOG_COLORS.WHITE)
            return SUCCESS_RETURN_CODE
        return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration python updater."""
        format = self.run_format()
        return format, SKIP_VALIDATE_PY_RETURN_CODE

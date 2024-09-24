import subprocess
from shutil import copy
from typing import Tuple

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE,
    SKIP_VALIDATE_PY_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdate

AUTOPEP_LINE_LENGTH = "130"


class PythonFileFormat(BaseUpdate):
    """PythonFileFormat class is designed to update python file according to Demisto's convention.

    Attributes:
        input (str): The path to the file we are updating at the moment.
        output (str): The desired file name to save the updated version of the python file to.
        path (str): Non relevant parameter - no schema for python files.
        from_version (str): Non relevant parameter - no fromversion field in python files.
        no_validate (bool): Whether the user specifies not to run validate after format.
    """

    def __init__(
        self,
        input: str = "",
        output: str = "",
        path: str = "",
        from_version: str = "",
        no_validate: bool = True,
        **kwargs,
    ):
        super().__init__(
            input=input,
            output=output,
            path=path,
            from_version=from_version,
            no_validate=no_validate,
            **kwargs,
        )

    @staticmethod
    def format_py_using_autopep(py_file_path):
        """Run autopep8 formatter on python file.
        Args:
            py_file_path (str): The python file path.
        Returns:
            bool. True if succeeded to run autopep8 on file, False otherwise.
        """
        logger.debug(f"\nRunning autopep8 on file: {py_file_path}\n")
        try:
            subprocess.call(
                [
                    "autopep8",
                    "-i",
                    "--max-line-length",
                    AUTOPEP_LINE_LENGTH,
                    py_file_path,
                ]
            )
        except FileNotFoundError:
            logger.info(
                "<yellow>autopep8 skipped! It doesn't seem you have autopep8 installed.\n "
                "Make sure to install it with: pip install autopep8.\n "
                "Then run: autopep8 -i {}</yellow>".format(py_file_path)
            )
            return False
        return True

    def create_output_file(self):
        """Create output file with the data of the source file."""
        copy(str(self.source_file), str(self.output_file))

    def run_format(self) -> int:
        logger.info(
            f"\n<blue>================= Updating file {self.source_file} =================</blue>"
        )
        py_file_path = self.source_file
        if self.output_file != self.source_file:
            self.create_output_file()
            py_file_path = self.output_file

        is_autopep_passed = self.format_py_using_autopep(py_file_path)
        if is_autopep_passed:
            return SUCCESS_RETURN_CODE
        return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration python updater."""
        format_res = self.run_format()
        return format_res, SKIP_VALIDATE_PY_RETURN_CODE

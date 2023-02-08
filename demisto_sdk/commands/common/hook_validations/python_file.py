from pathlib import Path

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)


class PythonFileValidator(BaseValidator):
    """PythonFileValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def __init__(
        self,
        file_path: str,
        ignored_errors=None,
        print_as_warnings=False,
        suppress_print=False,
        json_file_path=None,
        specific_validations=None,
    ):
        super().__init__(
            ignored_errors=ignored_errors,
            print_as_warnings=print_as_warnings,
            suppress_print=suppress_print,
            json_file_path=json_file_path,
            specific_validations=specific_validations,
        )

        self.file_path = Path(file_path)
        with open(self.file_path) as f:
            file_content = f.read()
        self.file_content = file_content

    @error_codes("BA119")
    def is_valid_copyright(self) -> bool:
        """
        Checks if there are words related to copyright section in the python file.

        Returns:
            True if related words does not exist in the file, and False if it does.
        """
        invalid_lines = []
        invalid_words = ["BSD", "MIT", "Copyright", "proprietary"]
        for line_num, line in enumerate(self.file_content.split("\n")):
            for text in invalid_words:
                if text in line.split():
                    invalid_lines.append(line_num + 1)

        if invalid_lines:
            error_message, error_code = Errors.copyright_section_in_python_error(
                invalid_lines
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def is_valid_file(self) -> bool:
        """Check whether the python file is valid or not
        Returns:
            bool: True if valid else False.
        """
        return all([self.is_valid_copyright()])

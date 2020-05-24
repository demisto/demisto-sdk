import click


class BaseValidator:

    def __init__(self, ignored_errors=None, print_as_warnings=False):
        self.ignored_errors = ignored_errors if ignored_errors else []
        self.print_as_warnings = print_as_warnings

    def should_ignore_error(self, error_code):
        """Return True is code should be ignored and False otherwise"""
        # check if specific codes are ignored
        if error_code in self.ignored_errors:
            return True

        # in case a whole section of codes are selected
        code_type = error_code[:2]
        if code_type in self.ignored_errors:
            return True

        return False

    def handle_error(self, error_massage, error_code, file_path, should_print=True, suggested_fix=None):
        """Handle an error that occurred during validation

        Args:
            suggested_fix(str): A suggested fix
            error_massage(str): The error message
            file_path(str): The file from which the error occurred
            error_code(str): The error code
            should_print(bool): whether the command should be printed

        Returns:
            str. Will return the formatted error message if it is not ignored, an None if it is ignored
        """
        formatted_error = f"{file_path}: [{error_code}] - {error_massage}".rstrip("\n") + "\n"

        if self.should_ignore_error(error_code):
            if should_print and self.print_as_warnings:
                click.secho(formatted_error, fg="yellow")
            return None

        if should_print:
            if suggested_fix:
                click.secho(formatted_error[:-1], fg="bright_red")
                click.secho(suggested_fix + "\n", fg="bright_red")

            else:
                click.secho(formatted_error, fg="bright_red")

        return formatted_error

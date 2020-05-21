import click


class BaseValidator:

    def __init__(self, ignored_errors=None, print_as_warnings=False):
        if ignored_errors is None:
            ignored_errors = []
        self.ignored_errors = ignored_errors
        self.print_as_warnings = print_as_warnings

    def handle_error(self, error_massage, error_code, should_print=True, suggested_fix=None):
        """Handle an error that occurred during validation

        Args:
            suggested_fix(str): A suggested fix
            error_massage(str): The error message
            error_code(str): The error code
            should_print(bool): whether the command should be printed

        Returns:
            str. Will return the formatted error message if it is not ignored, an None if it is ignored
        """
        formatted_error = "(" + error_code + ")" + " " + error_massage

        if error_code in self.ignored_errors:
            if should_print and self.print_as_warnings:
                click.secho(formatted_error, fg="yellow")
            return None

        if should_print:
            click.secho(formatted_error, fg="red")

        if suggested_fix:
            click.secho(suggested_fix, fg="red")

        return formatted_error

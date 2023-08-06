
from typing import List

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.validate_poc.validators.base_validator import ValidationResult


def post_results(self, results: List[ValidationResult] = [], only_throw_warning = []):
        is_valid = True
        for result in results:
            if not result.is_valid:
                if result.error_code in only_throw_warning:
                    logger.warning(f"[yellow]{result.format_message}[/yellow]")
                else:
                    logger.error(f"[red]{result.format_message}[/red]")
                    is_valid = False
        return is_valid

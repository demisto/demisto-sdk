from typing import Callable, Optional

import click

from demisto_sdk.commands.common.errors import Errors


def _is_valid_brand(brand_name: str, id_set_file: dict) -> bool:
    """
    Goes over the id_set_file and searches for the given brand_name
    Args:
        brand_name: name of the brand
        id_set_file: dict containing all entities information
    Returns:
        True if the brand_name exists in id_set_file, False otherwise
    """
    for integration_data in id_set_file['integrations']:
        if brand_name in integration_data:
            return True
    return False


def check_tasks_brands(current_file: dict, id_set_file: Optional[dict], file_path: str, handle_error: Callable) -> bool:
    """
    Checks that all the tasks' in a playbook which have a script also a have a valid brand name,
    Args:
        current_file: Playbook to validate
        id_set_file: id set file
        file_path: File path from which the error occurred
        handle_error: Callable which handles errors during validation
    Returns:
        True if all tasks who have a brand use a valid brand, False otherwise
    """
    is_valid = True

    if not id_set_file:
        click.secho("Skipping playbook brand name validation. Could not read id_set.json.", fg="yellow")
        return is_valid

    tasks: dict = current_file.get('tasks', {})
    for task_key, task in tasks.items():
        task_script = task.get('task', {}).get('script', None)
        if task_script is not None and '|||' in task_script:
            brand_name = task_script[:task_script.find('|||')]
            if not _is_valid_brand(brand_name, id_set_file):
                is_valid = False
                error_message, error_code = Errors.missing_brand_name_in_script(task_key, task_script)
                handle_error(error_message, error_code, file_path=file_path)
    return is_valid

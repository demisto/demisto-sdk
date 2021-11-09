import click
from demisto_sdk.commands.common.errors import Errors
from typing import Callable, Optional


def _is_associated(brand_name: str, id_set_file: dict) -> bool:
    for integration_data in id_set_file.get('integrations'):
        if brand_name in integration_data:
            return True
    return False


def check_task_brand(current_file: dict, id_set_file: Optional[dict], file_path: str, handle_error: Callable) -> bool:
    is_valid = True

    if not id_set_file:
        click.secho("Skipping playbook script id validation. Could not read id_set.json.", fg="yellow")
        return is_valid

    tasks: dict = current_file.get('tasks', {})
    for task_key, task in tasks.items():
        task_script = task.get('task', {}).get('script', None)
        if task_script is not None and '|||' in task_script:
            brand_name = task_script[:task_script.find('|||')]
            if not _is_associated(brand_name, id_set_file):
                is_valid = False
                error_message, error_code = Errors.missing_brand_name_in_script(task_key, task_script)
                handle_error(error_message, error_code, file_path=file_path)
    return is_valid

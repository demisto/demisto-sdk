import re
from typing import Callable, List

from demisto_sdk.commands.common.tools import run_command


def git_path() -> str:
    git_path = run_command('git rev-parse --show-toplevel')
    return git_path.replace('\n', '')


def get_current_working_branch() -> str:
    branches = run_command('git branch')
    branch_name_reg = re.search(r'\* (.*)', branches)
    if branch_name_reg:
        return branch_name_reg.group(1)

    return ''


def get_changed_files(from_branch: str = 'master', filter_results: Callable = None):
    temp_files = run_command(f'git diff --name-status {from_branch}').split('\n')
    files: List = []
    for file in temp_files:
        if file:
            temp_file_data = {
                'status': file[0]
            }
            if file.lower().startswith('r'):
                file = file.split('\t')
                temp_file_data['name'] = file[2]
            else:
                temp_file_data['name'] = file[2:]
            files.append(temp_file_data)

    if filter_results:
        filter(filter_results, files)

    return files

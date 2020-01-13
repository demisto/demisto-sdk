import re
from typing import Callable, List

from demisto_sdk.common.tools import run_command


def get_current_working_branch() -> str:
    branches = run_command('git branch')
    branch_name_reg = re.search(r'\* (.*)', branches)
    return branch_name_reg.group(1)


def get_changed_files(from_branch: str = 'master', filter_results: Callable = None):
    temp_files = run_command(f'git diff --name-status {from_branch}').split('\n')
    files: List = []
    for file in temp_files:
        if file:
            files.append({
                'name': file[2:],
                'status': file[0]
            })

    if filter_results:
        filter(filter_results, files)

    return files

import subprocess
import os
from demisto_sdk.commands.common.tools import print_error, print_warning


class ReadMeValidator:
    def __init__(self, file_path):
        self.file_path = file_path

    def is_file_valid(self) -> bool:
        is_valid = True
        mdx_parse = f'{os.path.dirname(os.path.abspath(__file__))}/../mdx-parse.js'
        try:
            # check if requiring modules in node exist
            is_node = subprocess.run(['node', '-v'], text=True, timeout=10, capture_output=True)
            is_mdx = subprocess.run(['npm', 'ls', '@mdx-js/mdx'], text=True, timeout=10, capture_output=True)
            is_fs_extra = subprocess.run(['npm', 'ls', 'fs-extra'], text=True, timeout=10, capture_output=True)
            is_commander = subprocess.run(['npm', 'ls', 'commander'], text=True, timeout=10, capture_output=True)
            if is_node.returncode == 0 and is_mdx.returncode == 0 and is_fs_extra.returncode == 0 and \
                    is_commander.returncode == 0:
                # run the java script mdx parse validator
                res = subprocess.run(['node', mdx_parse, '-f', self.file_path], text=True, timeout=10,
                                     capture_output=True)
                if res.returncode != 0:
                    print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {res.stderr}')
                    is_valid = False
            else:
                # if modules are not installed, the readme file would not be validated
                print_warning(f'There are some modules missing, Test Skipped,\n'
                              f'Status of node {is_node.returncode}\n '
                              f'Status of mdx package {is_mdx.returncode}\n status of fs_extra {is_fs_extra.returncode}'
                              f'\n '
                              f'Status of commander {is_commander.returncode}')
        except Exception as err:  # check if you can catch a more exact exception
            if "No such file or directory: 'node': 'node'" in str(err):
                print_warning(f'There is no node installed on the machine, Test Skipped, error {err}')
            else:
                print_error(f'Failed while verifying README.md, Path: {self.file_path}. Error Message is: {err}')
                is_valid = False
        return is_valid

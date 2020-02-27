import subprocess
import os
from demisto_sdk.commands.common.tools import print_error, print_warning


class ReadMeValidator:
    def __init__(self, file_path):
        self.file_path = file_path

    def is_file_valid(self):
        mdx_parse = f'{os.path.dirname(os.path.abspath(__file__))}/../mdx-parse.js'
        is_node = subprocess.run(['node', '-v'], text=True, timeout=10, capture_output=True)
        is_mdx = subprocess.run(['npm', 'ls', '@mdx-js/mdx'], text=True, timeout=10, capture_output=True)
        is_fs_extra = subprocess.run(['npm', 'ls', 'fs-extra'], text=True, timeout=10, capture_output=True)
        is_commander = subprocess.run(['npm', 'ls', 'commander'], text=True, timeout=10, capture_output=True)
        if is_node.returncode == 0 and is_mdx.returncode == 0 and is_fs_extra.returncode == 0 and is_commander.returncode == 0:
            res = subprocess.run(['node', mdx_parse, '-f', self.file_path], text=True, timeout=10, capture_output=True)
            if res.returncode != 0:
                print_error(f'Failed verfiying: {self.file_path}. Error: {res.stderr}')
                return False
        else:
            print_warning(
                f'There is no node or packages installed in your system.\n status of node {is_node.returncode}\n status of mdx package {is_mdx.returncode}\n status of fs_extra {is_fs_extra.returncode}\n status of commander {is_commander.returncode}')
            return None
        return True

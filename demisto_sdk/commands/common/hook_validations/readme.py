import subprocess
import os
from demisto_sdk.commands.common.tools import print_error, print_warning


class ReadMeValidator:
    def __init__(self, file_path):
        self.file_path = file_path
        self.is_valid = True
        self.ready = False

    def is_valid_file(self):
        """Check whether the readme file is valid or not
        """
        is_readme_valid = all([
            self.is_mdx_file(),
        ])
        return is_readme_valid

    def is_mdx_file(self) -> bool:
        mdx_parse = f'{os.path.dirname(os.path.abspath(__file__))}/../mdx-parse.js'
        self.are_modules_installed_for_verify()
        if self.ready:
            # run the java script mdx parse validator
            res = subprocess.run(['node', mdx_parse, '-f', self.file_path], text=True, timeout=10,
                                 capture_output=True)
            if res.returncode != 0:
                print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {res.stderr}')
                self.is_valid = False
        return self.is_valid

    def are_modules_installed_for_verify(self):
        try:
            # check if requiring modules in node exist
            is_node = subprocess.run(['node', '-v'], text=True, timeout=10, capture_output=True)
            is_mdx = subprocess.run(['npm', 'ls', '@mdx-js/mdx'], text=True, timeout=10, capture_output=True)
            is_fs_extra = subprocess.run(['npm', 'ls', 'fs-extra'], text=True, timeout=10, capture_output=True)
            is_commander = subprocess.run(['npm', 'ls', 'commander'], text=True, timeout=10, capture_output=True)
            if is_node.returncode == 0 and is_mdx.returncode == 0 and is_fs_extra.returncode == 0 and \
                    is_commander.returncode == 0:
                self.ready = True
        except Exception as err:
            if "No such file or directory: 'node': 'node'" in str(err):
                print_warning(f'There is no node installed on the machine, Test Skipped, error {err}')
            else:
                print_error(f'Failed while verifying README.md, Path: {self.file_path}. Error Message is: {err}')
                self.is_valid = False
        return self.ready

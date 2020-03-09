import subprocess
import os
from demisto_sdk.commands.common.tools import print_error, print_warning

NODE_MODULES_DIRECTORY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(__file__)))))


class ReadMeValidator:
    """ReadMeValidator is a validator for readme.md files
        In order to run the validator correctly please make sure:
        - Node installed on you machine
        - Node-modules folder should be in demisto-sdk folder
        - make sure that the module '@mdx-js/mdx' , 'fs-extra', 'commander' are installed in node-modules folder
        If not installed the validator will print warning with relevant module that is missing , please install
        using " npm install *missing_module_name* "
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def is_valid_file(self):
        """Check whether the readme file is valid or not
        """
        is_readme_valid = all([
            self.is_mdx_file(),
        ])
        return is_readme_valid

    def is_mdx_file(self) -> bool:
        mdx_parse = f'{os.path.dirname(os.path.abspath(__file__))}/../mdx-parse.js'
        ready, is_valid = self.are_modules_installed_for_verify()
        if ready:
            # run the java script mdx parse validator
            res = subprocess.run(['node', mdx_parse, '-f', self.file_path], text=True, timeout=10,
                                 capture_output=True)
            if res.returncode != 0:
                print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {res.stderr}')
                is_valid = False
        return is_valid

    def are_modules_installed_for_verify(self):
        is_valid = True
        ready = False
        try:
            # check if requiring modules in node exist
            is_node = subprocess.run(['node', '-v'], text=True, timeout=10, capture_output=True,
                                     cwd=NODE_MODULES_DIRECTORY)
            is_mdx = subprocess.run(['npm', 'ls', '@mdx-js/mdx'], text=True, timeout=10, capture_output=True,
                                    cwd=NODE_MODULES_DIRECTORY)
            is_fs_extra = subprocess.run(['npm', 'ls', 'fs-extra'], text=True, timeout=10, capture_output=True,
                                         cwd=NODE_MODULES_DIRECTORY)
            is_commander = subprocess.run(['npm', 'ls', 'commander'], text=True, timeout=10, capture_output=True,
                                          cwd=NODE_MODULES_DIRECTORY)
            print(NODE_MODULES_DIRECTORY)
            if is_node.returncode == 0 and is_mdx.returncode == 0 and is_fs_extra.returncode == 0 and \
                    is_commander.returncode == 0:
                ready = True
            else:
                if is_mdx.returncode:
                    print_warning(f"The npm module: @mdx-js/mdx is not installed"
                                  f" directory:{NODE_MODULES_DIRECTORY}, Test Skipped")
                if is_fs_extra.returncode:
                    print_warning(f"The npm module: fs-extra is not installed"
                                  f" directory: {NODE_MODULES_DIRECTORY}, Test Skipped")
                if is_commander.returncode:
                    print_warning(f"The npm module: commander is not installed"
                                  f" directory: {NODE_MODULES_DIRECTORY}, Test Skipped")
                print_warning(f"The correct directory for node-modules folder should be in {NODE_MODULES_DIRECTORY}")
        except Exception as err:
            if "No such file or directory: 'node': 'node'" in str(err):
                print_warning(f'There is no node installed on the machine, Test Skipped, warning: {err}')
            else:
                print_error(f'Failed while verifying README.md, Path: {self.file_path}. Error Message is: {err}')
                is_valid = False
        return ready, is_valid

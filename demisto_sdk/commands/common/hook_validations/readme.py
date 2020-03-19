import subprocess
import os
from demisto_sdk.commands.common.tools import print_error, print_warning


class ReadMeValidator:
    """ReadMeValidator is a validator for readme.md files
        In order to run the validator correctly please make sure:
        - Node is installed on you machine
        - make sure that the module '@mdx-js/mdx', 'fs-extra', 'commander' are installed in node-modules folder.
            If not installed, the validator will print a warning with the relevant module that is missing.
            please install it using "npm install *missing_module_name*"
        - 'DEMISTO_README_VALIDATION' environment variable should be set to True.
            To set the environment variables, run the following shell commands:
            export DEMISTO_README_VALIDATION=True
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def is_valid_file(self):
        """Check whether the readme file is valid or not
        """
        if os.environ.get('DEMISTO_README_VALIDATION'):
            is_readme_valid = all([
                self.is_mdx_file(),
            ])
            return is_readme_valid
        else:
            return True

    def is_mdx_file(self) -> bool:
        ready, is_valid = self.are_modules_installed_for_verify()
        if ready:
            mdx_parse = f'{os.path.dirname(os.path.abspath(__file__))}/../mdx-parse.js'
            # run the java script mdx parse validator
            res = subprocess.run(['node', mdx_parse, '-f', self.file_path], text=True, timeout=10,
                                 capture_output=True)
            if res.returncode != 0:
                print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {res.stderr}')
                is_valid = False
        return is_valid

    def are_modules_installed_for_verify(self):
        node_modules_directory = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.join(__file__))))))
        is_valid = True
        ready = False
        try:
            # check if requiring modules in node exist
            is_node = subprocess.run(['node', '-v'], text=True, timeout=10, capture_output=True,
                                     cwd=node_modules_directory)
            is_mdx = subprocess.run(['npm', 'ls', '@mdx-js/mdx'], text=True, timeout=10, capture_output=True,
                                    cwd=node_modules_directory)
            is_fs_extra = subprocess.run(['npm', 'ls', 'fs-extra'], text=True, timeout=10, capture_output=True,
                                         cwd=node_modules_directory)
            is_commander = subprocess.run(['npm', 'ls', 'commander'], text=True, timeout=10, capture_output=True,
                                          cwd=node_modules_directory)
            if is_node.returncode == 0 and is_mdx.returncode == 0 and is_fs_extra.returncode == 0 and \
                    is_commander.returncode == 0:
                ready = True
            else:
                if is_mdx.returncode:
                    print_warning(f"The npm module: @mdx-js/mdx is not installed in the "
                                  f" directory:{node_modules_directory}, Test Skipped.")
                if is_fs_extra.returncode:
                    print_warning(f"The npm module: fs-extra is not installed in the "
                                  f" directory: {node_modules_directory}, Test Skipped.")
                if is_commander.returncode:
                    print_warning(f"The npm module: commander is not installed in the "
                                  f"directory: {node_modules_directory}, Test Skipped.")
        except Exception as err:
            if "No such file or directory: 'node': 'node'" in str(err):
                print_warning(f'There is no node installed on the machine, Test Skipped, warning: {err}')
            else:
                print_error(f'Failed while verifying README.md, Path: {self.file_path}. Error Message is: {err}')
                is_valid = False
        return ready, is_valid

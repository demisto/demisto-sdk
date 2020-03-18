from pathlib import Path
import os
from demisto_sdk.commands.common.tools import print_error, print_warning, run_command_os, get_content_path


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

    def __init__(self, file_path: str):
        self.content_path = get_content_path()
        self.file_path = Path(file_path)
        self.pack_path = self.file_path.parent

    def is_valid_file(self) -> bool:
        """Check whether the readme file is valid or not

        Returns:
            bool: True if env configured else Fale.
        """
        if os.environ.get('DEMISTO_README_VALIDATION') or os.environ.get('CI'):
            return self.is_mdx_file()
        else:
            return True

    def is_mdx_file(self) -> bool:
        valid = self.are_modules_installed_for_verify()
        if valid:
            mdx_parse = Path(__file__).parent.parent / 'mdx-parse.js'
            # run the java script mdx parse validator
            _, stderr, is_valid = run_command_os(f'node {mdx_parse} -f {self.file_path}', cwd=self.content_path)
            if is_valid:
                print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {stderr}')
                return False
        return True

    def are_modules_installed_for_verify(self) -> bool:
        """ Check the following:
            1. npm packages installed - see packs var for specific pack details.
            2. node interperter exists.

        Returns:
            bool: True If all req ok else False
        """
        valid = True
        # Check node exist
        stdout, stderr, exit_code = run_command_os('node -v', cwd=self.content_path)
        if exit_code:
            print_warning(f'There is no node installed on the machine, Test Skipped, error - {stderr}, {stdout}')
            valid = False
        else:
            # Check npm modules exsits
            missing_packs = False
            packs = ['@mdx-js/mdx', 'fs-extra', 'commander']
            for pack in packs:
                stdout, stderr, exit_code = run_command_os(f'npm ls {pack}', cwd=self.content_path)
                if exit_code:
                    missing_packs = True
                    print_warning(f"The npm module: {pack} is not installed.")

            # Install node modules
            if missing_packs:
                stdout, stderr, exit_code = run_command_os(f'npm install .', cwd=self.content_path)
                if not exit_code:
                    print(f"The npm modules: Installed succesfully")
                else:
                    print(f"The npm modules: Installation failed")
                    valid = False

        return valid

from subprocess import Popen, PIPE
from pathlib import Path
from typing import Tuple
import shlex
import os
import git
from demisto_sdk.commands.common.tools import print_error, print_warning


def get_content_path() -> str:
    """ Get abs content path, from any CWD

    Returns:
        str: Absolute content path
    """
    git_repo = ""
    try:
        git_repo = git.Repo(os.getcwd(),
                            search_parent_directories=True)
        if 'content' not in git_repo.remote().urls.__next__():
            raise git.InvalidGitRepositoryError
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        print_error("Please run demisto-sdk lint in content repository - Aborting!")

    return git_repo.working_dir


def run_command_os(command: str, cwd: Path) -> Tuple[str, str, int]:
    """ Run command in subprocess tty

    Args:
        command(str): Command to be executed.
        cwd(Path): Path from pathlib object to be executed

    Returns:
        str: Stdout of the command
        str: Stderr of the command
        int: exit code of command
    """
    try:
        process = Popen(shlex.split(command),
                        cwd=cwd,
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True)
        stdout, stderr = process.communicate()
    except OSError as e:
        return '', str(e), 1

    return stdout, stderr, process.returncode


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
        self.file_path = self.content_path / Path(file_path)
        self.pack_path = self.file_path.parent

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
            mdx_parse = Path(__file__).parent.parent / 'mdx-parse.js'
            # run the java script mdx parse validator
            stdout, stderr, returncode = run_command_os(f'node {mdx_parse} -f {self.file_path}', cwd=self.content_path)
            if returncode != 0:
                print_error(f'Failed verifying README.md, Path: {self.file_path}. Error Message is: {stderr}')
                is_valid = False
        return is_valid

    def are_modules_installed_for_verify(self):
        is_valid = True
        ready = False
        try:
            # check if requiring modules in node exist
            _, _, is_node = run_command_os('node -v', cwd=self.pack_path)
            _, _, is_mdx = run_command_os('npm ls -g @mdx-js/mdx', cwd=self.pack_path)
            _, _, is_fs_extra = run_command_os('npm ls -g fs-extra', cwd=self.pack_path)
            _, _, is_commander = run_command_os('npm ls -g commander', cwd=self.pack_path)

            if not is_node and not is_mdx and not is_fs_extra and not is_commander:
                ready = True
            else:
                if is_mdx:
                    print_warning(f"The npm module: @mdx-js/mdx is not installed in the, Test Skipped.")
                if is_fs_extra:
                    print_warning(f"The npm module: fs-extra is not installed in the Test Skipped.")
                if is_commander:
                    print_warning(f"The npm module: commander is not installed in the, Test Skipped.")
        except Exception as err:
            if "No such file or directory: 'node': 'node'" in str(err):
                print_warning(f'There is no node installed on the machine, Test Skipped, warning: {err}')
            else:
                print_error(f'Failed while verifying README.md, Path: {self.file_path}. Error Message is: {err}')
                is_valid = False

        return ready, is_valid

# STD python packages
import io
import logging
import os
import re
import shlex
import shutil
import tarfile
import textwrap
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Dict, Generator, List, Optional, Union

# Third party packages
import docker
import docker.errors
import git
import requests
# Local packages
from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.common.tools import print_warning, run_command_os
from docker.models.containers import Container

# Python2 requirements
PYTHON2_REQ = ["flake8", "vulture"]

# Define check exit code if failed
EXIT_CODES = {
    "flake8": 0b1,
    "XSOAR_linter": 0b1000000000,
    "bandit": 0b10,
    "mypy": 0b100,
    "vulture": 0b1000,
    "pytest": 0b10000,
    "pylint": 0b100000,
    "pwsh_analyze": 0b1000000,
    "pwsh_test": 0b10000000,
    "image": 0b100000000,
}

# Execution exit codes
SUCCESS = 0b0
FAIL = 0b1
RERUN = 0b10
WARNING = 0b100

# Power shell checks
PWSH_CHECKS = ["pwsh_analyze", "pwsh_test"]
PY_CHCEKS = ["flake8", "XSOAR_linter", "bandit", "mypy", "vulture", "pytest", "pylint"]

# Line break
RL = '\n'

logger = logging.getLogger('demisto-sdk')


def validate_env() -> None:
    """Packs which use python2 will need to be run inside virtual environment including python2 as main
    and the specified req
    """
    wrn_msg = 'demisto-sdk lint not in virtual environment, Python2 lints will fail, use "source .hooks/bootstrap"' \
              ' to create the virtual environment'
    command = "python -c \"import sys; print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))\""
    stdout, stderr, exit_code = run_command_os(command, cwd=Path().cwd())
    if "2" not in stdout:
        print_warning(wrn_msg)
    else:
        stdout, stderr, exit_code = run_command_os("pip3 freeze", cwd=Path().cwd())
        for req in PYTHON2_REQ:
            if req not in stdout:
                print_warning(wrn_msg)


def build_skipped_exit_code(no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool, no_vulture: bool,
                            no_xsoar_linter: bool,
                            no_test: bool, no_pwsh_analyze: bool, no_pwsh_test: bool, docker_engine: bool) -> float:
    """
    no_flake8(bool): Whether to skip flake8.
    no_xsoar_linter(bool): Whether to skip xsoar linter.
    no_bandit(bool): Whether to skip bandit.
    no_mypy(bool): Whether to skip mypy.
    no_vulture(bool): Whether to skip vulture
    no_pylint(bool): Whether to skip pylint.
    no_test(bool): Whether to skip pytest.
    docker_engine(bool): docker engine exists.
    """
    skipped_code = 0b0
    # When the CI env var is not set - on local env - check if any linters should be skipped
    # Otherwise - When the CI env var is set - Run all linters without skipping
    if not os.environ.get('CI'):
        if no_flake8:
            skipped_code |= EXIT_CODES["flake8"]
        if no_xsoar_linter:
            skipped_code |= EXIT_CODES["XSOAR_linter"]
        if no_bandit:
            skipped_code |= EXIT_CODES["bandit"]
        if no_mypy:
            skipped_code |= EXIT_CODES["mypy"]
        if no_vulture:
            skipped_code |= EXIT_CODES["vulture"]
        if no_pylint or not docker_engine:
            skipped_code |= EXIT_CODES["pylint"]
        if no_test or not docker_engine:
            skipped_code |= EXIT_CODES["pytest"]
        if no_pwsh_analyze or not docker_engine:
            skipped_code |= EXIT_CODES["pwsh_analyze"]
        if no_pwsh_test or not docker_engine:
            skipped_code |= EXIT_CODES["pwsh_test"]

    return skipped_code


def get_test_modules(content_repo: Optional[git.Repo], is_external_repo: bool) -> Dict[Path, bytes]:
    """ Get required test modules from content repository - {remote}/master
    1. Tests/demistomock/demistomock.py
    2. Tests/scripts/dev_envs/pytest/conftest.py
    3. Scripts/CommonServerPython/CommonServerPython.py
    4. CommonServerUserPython.py

    Returns:
        dict: path and file content - see below modules dict
    """
    if is_external_repo:
        modules = [Path("demistomock.py"),
                   Path("dev_envs/pytest/conftest.py"),
                   Path("CommonServerPython.py"),
                   Path("demistomock.ps1"),
                   Path("CommonServerPowerShell.ps1")
                   ]
    else:
        modules = [Path("Tests/demistomock/demistomock.py"),
                   Path("Tests/scripts/dev_envs/pytest/conftest.py"),
                   Path("Packs/Base/Scripts/CommonServerPython/CommonServerPython.py"),
                   Path("Tests/demistomock/demistomock.ps1"),
                   Path("Packs/Base/Scripts/CommonServerPowerShell/CommonServerPowerShell.ps1")
                   ]
    modules_content = {}
    if content_repo:
        # Trying to get file from local repo before downloading from GitHub repo (Get it from disk), Last fetch
        for module in modules:
            try:
                modules_content[module] = (content_repo.working_dir / module).read_bytes()
            except FileNotFoundError:
                logger.warning(f'Module {module} was not found, possibly deleted due to being in a feature branch')
    else:
        # If not succeed to get from local repo copy, Download the required modules from GitHub
        for module in modules:
            url = f'https://raw.githubusercontent.com/demisto/content/master/{module}'
            for trial in range(2):
                res = requests.get(url=url,
                                   verify=False)
                if res.ok:
                    # ok - not 4XX or 5XX
                    modules_content[module] = res.content
                    break
                elif trial == 2:
                    raise requests.exceptions.ConnectionError

    modules_content[Path("CommonServerUserPython.py")] = b''

    return modules_content


@contextmanager
def add_typing_module(lint_files: List[Path], python_version: float):
    """ Check for typing import for python2 packages
            1. Entrance - Add import typing in the begining of the file.
            2. Closing - change back to original.

        Args:
            lint_files(list): File to execute lint - for adding typing in python 2.7
            python_version(float): The package python version.

        Raises:
            IOError: if can't write to files due permissions or other reasons
    """
    added_modules: List[Path] = []
    back_lint_files: List[Path] = []
    try:
        # Add typing import if needed to python version 2 packages
        if python_version < 3:
            for lint_file in lint_files:
                data = lint_file.read_text(encoding="utf-8")
                typing_regex = "(from typing import|import typing)"
                module_match = re.search(typing_regex, data)
                if not module_match:
                    original_file = lint_file
                    back_file = lint_file.with_suffix('.bak')
                    original_file.rename(back_file)
                    data = back_file.read_text()
                    original_file.write_text("from typing import *  # noqa: F401" + '\n' + data)
                    back_lint_files.append(back_file)
                    added_modules.append(original_file)
        yield
    except Exception:
        pass
    finally:
        for added_module in added_modules:
            if added_module.exists():
                added_module.unlink()
        for back_file in back_lint_files:
            if back_file.exists():
                original_name = back_file.with_suffix('.py')
                back_file.rename(original_name)


@contextmanager
def add_tmp_lint_files(content_repo: git.Repo, pack_path: Path, lint_files: List[Path], modules: Dict[Path, bytes],
                       pack_type: str):
    """ LintFiles is context manager to mandatory files for lint and test
            1. Entrance - download missing files to pack.
            2. Closing - Remove downloaded files from pack.

        Args:
            pack_path(Path): Absolute path of pack
            lint_files(list): File to execute lint - for adding typing in python 2.7
            modules(dict): modules content to locate in pack path
            content_repo(Path): Repository object
            pack_type(st): Pack type.

        Raises:
            IOError: if can't write to files due permissions or other reasons
    """
    added_modules: List[Path] = []
    try:
        # Add mandatory test,lint modules
        for module, content in modules.items():
            pwsh_module = TYPE_PWSH == pack_type and module.suffix == '.ps1'
            python_module = TYPE_PYTHON == pack_type and module.suffix == '.py'
            if pwsh_module or python_module:
                cur_path = pack_path / module.name
                if not cur_path.exists():
                    cur_path.write_bytes(content)
                    added_modules.append(cur_path)
        if pack_type == TYPE_PYTHON:
            # Append empty so it will exists
            cur_path = pack_path / "CommonServerUserPython.py"
            if not cur_path.exists():
                cur_path.touch()
                added_modules.append(cur_path)

            # Add API modules to directory if needed
            module_regex = r'from ([\w\d]+ApiModule) import \*(?:  # noqa: E402)?'
            for lint_file in lint_files:
                module_name = ""
                data = lint_file.read_text()
                module_match = re.search(module_regex, data)
                if module_match:
                    module_name = module_match.group(1)
                    rel_api_path = Path('Packs/ApiModules/Scripts') / module_name / f'{module_name}.py'
                    cur_path = pack_path / f'{module_name}.py'
                    if content_repo:
                        module_path = content_repo / rel_api_path
                        shutil.copy(src=module_path,
                                    dst=cur_path)
                    else:
                        url = f'https://raw.githubusercontent.com/demisto/content/master/{rel_api_path}'
                        api_content = requests.get(url=url,
                                                   verify=False).content
                        cur_path.write_bytes(api_content)

                    added_modules.append(cur_path)
        yield
    except Exception as e:
        logger.error(f'add_tmp_lint_files unexpected exception: {str(e)}')
        raise
    finally:
        # If we want to change handling of files after finishing - do it here
        pass


@lru_cache(maxsize=100)
def get_python_version_from_image(image: str) -> float:
    """ Get python version from docker image

    Args:
        image(str): Docker image id or name

    Returns:
        float: Python version X.Y (3.7, 3.6, ..)
    """
    docker_client = docker.from_env()
    py_num = 2.7
    # Run two times
    for _ in range(2):
        try:
            command = "python -c \"import sys; print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))\""

            container_obj: Container = docker_client.containers.run(
                image=image,
                command=shlex.split(command),
                detach=True
            )
            # Wait for container to finish
            container_obj.wait(condition="exited")
            # Get python version
            py_num = container_obj.logs()
            if isinstance(py_num, bytes):
                py_num = float(py_num)
            else:
                raise docker.errors.ContainerError
            for _ in range(2):
                # Try to remove the container two times.
                try:
                    container_obj.remove(force=True)
                    break
                except docker.errors.APIError:
                    pass
        except (docker.errors.APIError, docker.errors.ContainerError):
            continue

    return py_num


def get_file_from_container(container_obj: Container, container_path: str, encoding: str = "") -> Union[str, bytes]:
    """ Copy file from container.

    Args:
        container_obj(Container): Container ID to copy file from
        container_path(Path): Path in container image (file)
        encoding(str): valid encoding e.g. utf-8

    Returns:
        str or bytes: file as string decoded in utf-8

    Raises:
        IOError: Raise IO error if unable to create temp file
    """
    data: Union[str, bytes] = b''
    archive, stat = container_obj.get_archive(container_path)
    file_like = io.BytesIO(b"".join(b for b in archive))
    tar = tarfile.open(fileobj=file_like)
    before_read = tar.extractfile(stat['name'])
    if isinstance(before_read, io.BufferedReader):
        data = before_read.read()
    if encoding and isinstance(data, bytes):
        data = data.decode(encoding)

    return data


def copy_dir_to_container(container_obj: Container, host_path: Path, container_path: Path):
    """ Copy all content directory from container.

    Args:
        container_obj(Container): Container ID to copy file from
        host_path(Path): Path in host (directory)
        container_path(Path): Path in container (directory)

    Returns:
        str: file as string decode as utf-8

    Raises:
        IOError: Rase IO error if unable to create temp file
    """
    excluded_regex = "(__init__.py|.*.back)"
    file_like_object = io.BytesIO()
    old_cwd = os.getcwd()
    with tarfile.open(fileobj=file_like_object, mode='w:gz') as archive:
        os.chdir(host_path)
        archive.add('.', recursive=True, filter=lambda tarinfo: (
            tarinfo if not re.search(excluded_regex, Path(tarinfo.name).name) else None))
        os.chdir(old_cwd)

    for trial in range(2):
        status = container_obj.put_archive(path=container_path,
                                           data=file_like_object.getvalue())
        if status:
            break
        elif trial == 1:
            raise docker.errors.APIError(message="unable to copy dir to container")


def stream_docker_container_output(streamer: Generator) -> None:
    """ Stream container logs

    Args:
        streamer(Generator): Generator created by docker-sdk
    """
    try:
        wrapper = textwrap.TextWrapper(initial_indent='\t',
                                       subsequent_indent='\t',
                                       width=150)
        for chunk in streamer:
            logger.info(wrapper.fill(str(chunk.decode('utf-8'))))
    except Exception:
        pass


@contextmanager
def pylint_plugin(dest: Path):
    """
    Function which links the given path with the content of pylint plugins folder in resources.
    The main purpose is to link each pack with the pylint plugins.
    Args:
        dest: Pack path.
    """
    plugin_dirs = Path(__file__).parent / 'resources' / 'pylint_plugins'

    try:
        for file in plugin_dirs.iterdir():
            if file.is_file() and file.name != '__pycache__' and file.name.split('.')[1] != 'pyc':
                os.link(file, dest / file.name)

        yield
    finally:
        for file in plugin_dirs.iterdir():
            if file.is_file() and file.name != '__pycache__' and file.name.split('.')[1] != 'pyc':
                (dest / f'{file.name}').unlink()


def split_warnings_errors(output: str):
    """
        Function which splits the given string into warning messages and error using W or E in the beginning of string
        For error messages that do not start with E , they will be returned as other.
        The output of a certain pack can both include:
            - Fail msgs
            - Fail msgs and warnings msgs
            - Passed msgs
            - Passed msgs and warnings msgs
            - warning msgs
        Args:
            output(str): string which contains messages from linters.
        return:
            list of error messags, list of warnings messages, list of all undetected messages
        """
    output_lst = output.split('\n')
    # Warnings and errors lists currently relevant for XSOAR Linter
    warnings_list = []
    error_list = []
    # Others list is relevant for mypy and flake8.
    other_msg_list = []
    for msg in output_lst:
        # 'W:' for python2 xsoar linter
        # 'W[0-9]' for python3 xsoar linter
        if (msg.startswith('W') and msg[1].isdigit()) or 'W:' in msg or 'W90' in msg:
            warnings_list.append(msg)
        elif (msg.startswith('E') and msg[1].isdigit()) or 'E:' in msg or 'E90' in msg:
            error_list.append(msg)
        else:
            other_msg_list.append(msg)

    return error_list, warnings_list, other_msg_list

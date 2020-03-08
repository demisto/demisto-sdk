# STD python packages
import os
import shutil
import mmap
import tarfile
from functools import lru_cache
import io
from pathlib import Path
import re
from typing import List, Tuple
import shlex
from subprocess import Popen, PIPE
from contextlib import contextmanager
# Third party packages
import git
import docker.errors
import docker
from docker.models.containers import Container

# Define check exit code if failed
FAIL_EXIT_CODES = {
    "flake8": 0b1,
    "bandit": 0b10,
    "mypy": 0b100,
    "vulture": 0b1000000,
    "pytest": 0b1000,
    "pylint": 0b10000,
    "image": 0b100000
}


def get_test_modules(content_repo: git.Repo) -> dict:
    """ Get required test modules from content repository - {remote}/master
    1. Tests/demistomock/demistomock.py
    2. Tests/scripts/dev_envs/pytest/conftest.py
    3. Scripts/CommonServerPython/CommonServerPython.py
    4. CommonServerUserPython.py

    Returns:
        dict: path and file content - see below modules dict
    """
    modules = ["Tests/demistomock/demistomock.py",
               "Tests/scripts/dev_envs/pytest/conftest.py",
               "Scripts/CommonServerPython/CommonServerPython.py"]
    modules_content = {}
    remote = content_repo.remote()
    remote.fetch()
    for module in modules:
        modules_content[os.path.basename(module)] = content_repo.commit(f'{remote.name}/master').tree[
            module].data_stream.read()

    modules_content["CommonServerUserPython.py"] = b''

    return modules_content


@contextmanager
def create_tmp_lint_files(content_path: Path, pack_path: Path, lint_files: List[Path], modules: dict,
                          version_two: bool):
    """ LintFiles is context manager to mandatory files for lint and test
            1. Entrance - download missing files to pack.
            2. Closing - Remove downloaded files from pack.

        Args:
            pack_path(Path): abs path of pack
            lint_files(list): file to execute lint - for adding typing in python 2.7
            modules(dict): modules content to locate in pack path
            content_path(Path): content absolute path
            version_two(bool): wheter package support Python version 2

        Raises:
            IOError: if can't write to files due permissions or other reasons

    """
    added_modules: List[Path] = []
    try:
        # Add mandatory test,lint modules
        for module, content in modules.items():
            cur_path = pack_path / module
            if not cur_path.exists():
                cur_path.write_bytes(content)
                added_modules.append(cur_path)

        # Append empty so it will exists
        cur_path = pack_path / "CommonServerUserPython.py"
        if not cur_path.exists():
            cur_path.touch()
            added_modules.append(cur_path)

        # Add API modules to directory if needed
        module_regex = r'from ([\w\d]+ApiModule) import \*(?:  # noqa: E402)?'
        for lint_file in lint_files:
            module_name = ""
            data = lint_file.read_text(encoding="utf-8")
            module_match = re.search(module_regex, data)
            if module_match:
                module_name = module_match.group(1)
            if module_name:
                module_path = content_path / 'Packs/ApiModules/Scripts' / module_name / f'{module_name}.py'
                cur_path = pack_path / f'{module_name}.py'
                shutil.copy(src=module_path,
                            dst=cur_path)
                added_modules.append(cur_path)

        # Add typing import if needed to python version 2 packages
        if version_two:
            for lint_file in lint_files:
                with open(file=lint_file) as f:
                    s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                    if s.find(b"from typing import") == -1 or s.find(b"import typing") == -1:
                        lint_files.remove(lint_file)
                        tmp_lint_file = lint_file.with_suffix('.tmp')
                        lint_files.append(tmp_lint_file)
                        shutil.copyfile(lint_file, tmp_lint_file)
                        with open(tmp_lint_file, 'a+') as f_tmp:
                            content = f_tmp.read()
                            f_tmp.seek(0)
                            f_tmp.write("from typing import *".rstrip('\r\n') + '\n' + content)
                        added_modules.append(tmp_lint_file)

        yield lint_files
    finally:
        for added_module in added_modules:
            if added_module.exists():
                added_module.unlink()


@lru_cache(maxsize=100)
def get_python_version_from_image(image: str) -> float:
    """ Get python version from docker image

    Args:
        image(str): Docker image id or name

    Returns:
        float: Python version X.Y (3.7, 3.6, ..)
    """
    docker_client = docker.from_env()
    container_obj: Container = None
    py_num = ""
    for trial1 in range(2):
        try:
            command = "python -c \"import sys; print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))\""

            container_obj: Container = docker_client.containers.run(image=image,
                                                                    command=shlex.split(command),
                                                                    detach=True)
            # Wait for container to finish
            container_obj.wait(condition="exited")
            # Get python version
            py_num = container_obj.logs()
            if isinstance(py_num, bytes):
                py_num = float(py_num)
                break
            else:
                raise docker.errors.ContainerError
        except (docker.errors.APIError, docker.errors.ContainerError):
            continue

    if container_obj:
        for trial2 in range(2):
            try:
                container_obj.remove(force=True)
                break
            except docker.errors.APIError:
                continue

    return py_num


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


def get_file_from_container(container_obj: Container, container_path: str, encoding: str = "") -> str:
    """ Copy file from container.

    Args:
        container_obj(Container): Container ID to copy file from
        container_path(str): Path in container image (file)
        encoding(str): valide encoding e.g. utf-8

    Returns:
        str: file as string decode as utf-8

    Raises:
        IOError: Rase IO error if unable to create temp file
    """
    archive, stat = container_obj.get_archive(container_path)
    filelike = io.BytesIO(b"".join(b for b in archive))
    tar = tarfile.open(fileobj=filelike)
    data = tar.extractfile(stat['name']).read()
    if encoding:
        data = data.decode(encoding)

    return data

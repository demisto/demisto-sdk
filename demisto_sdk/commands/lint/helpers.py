# STD python packages
import os
import shutil
import mmap
import tarfile
from functools import lru_cache
import io
# Third party packages
import git
import docker.errors
import docker
from docker.models.containers import Container
# Local packages
from demisto_sdk.commands.unify.unifier import Unifier


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


class LintFiles:
    """ LintFiles is context manager to mandatory files for lint and test
            1. Entrance - download missing files to pack.
            2. Closing - Remove downloaded files from pack.

        Attributes:
            pack_path(str): abs path of pack
            lint_files(list): file to execute lint - for adding typing in python 2.7
            modules(dict): modules content to locate in pack path
            content_path(str): content absolute path

        Raises:
            IOError: if can't write to files due permissions or other reasons

    """

    def __init__(self, pack_path: str, lint_files: list, modules: dict, content_path: str, version_two: bool):
        self._pack_path = pack_path
        self._content_path = content_path
        self._lint_files = lint_files
        self._modules = modules
        self._added_modules = []
        self._version_two = version_two

    def __enter__(self):
        # Add mandatory test,lint modules
        for module, content in self._modules.items():
            cur_path = os.path.join(self._pack_path, module)
            if not os.path.exists(cur_path):
                with open(file=cur_path, mode="bw") as f:
                    f.write(content)
                self._added_modules.append(cur_path)

        # Append empty so it will exists
        cur_path = os.path.join(self._pack_path, "CommonServerUserPython.py")
        open(file=cur_path, mode="a").close()
        self._added_modules.append(cur_path)

        # Add API modules to directory if needed
        unifier = Unifier(self._pack_path)
        code_file_path = unifier.get_code_file('.py')
        with open(code_file_path, encoding='utf-8') as script_file:
            _, module_name = unifier.check_api_module_imports(script_file.read())
        if module_name:
            module_path = os.path.join(
                self._content_path, f'Packs/ApiModules/Scripts/{module_name}'
                                    f'/{module_name}.py')
            cur_path = os.path.join(self._pack_path, module_name + ".py")
            shutil.copy(module_path, cur_path)
            self._added_modules.append(cur_path)

        # Add typing import if needed to python version 2 packages
        if self._version_two:
            for lint_file in self._lint_files:
                with open(file=lint_file) as f:
                    s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                    if s.find(b"from typing import") == -1 or s.find(b"import typing") == -1:
                        self._lint_files.remove(lint_file)
                        self._lint_files.append(f"{lint_file}_tmp")
                        shutil.copyfile(lint_file, f"{lint_file}_tmp")
                        lint_file = f"{lint_file}_tmp"
                        with open(lint_file, 'a+') as f_tmp:
                            content = f_tmp.read()
                            f_tmp.seek(0)
                            f_tmp.write("from typing import *".rstrip('\r\n') + '\n' + content)
                        self._added_modules.append(lint_file)

        return self._lint_files

    def __exit__(self, *args):
        for added_module in self._added_modules:
            if os.path.exists(added_module):
                os.remove(added_module)


@lru_cache(maxsize=100)
def get_python_version_from_image(image: str) -> str:
    """ Get python version from docker image

    Args:
        image(str): Docker image id or name

    Returns:
        str: Python version X.Y (3.7, 3.6, ..)
    """
    docker_client = docker.from_env()
    container_obj: Container = None
    py_num = ""
    for trial1 in range(2):
        try:
            command = "import sys;print('{}.{}'.format (sys.version_info[0], sys.version_info[1]))"
            container_obj: Container = docker_client.containers.run(image=image,
                                                                    command=["/bin/sh", "-c",
                                                                             f"python -c \"{command}\""],
                                                                    detach=True)
            # Wait for container to finish
            container_obj.wait(condition="exited")
            # Get python version
            py_num = container_obj.logs()
            if isinstance(py_num, bytes):
                py_num = py_num.decode('utf-8').split('\n')[0]
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

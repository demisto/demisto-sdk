# STD python packages
import io
import os
import re
import shutil
import sqlite3
import tarfile
import textwrap
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Generator, List, Union

# Third party packages
import coverage
import docker
import docker.errors
import requests
from docker.models.containers import Container
from packaging.version import parse

# Local packages
from demisto_sdk.commands.common.constants import (
    TYPE_PWSH,
    TYPE_PYTHON,
    DemistoException,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger

# Python2 requirements
from demisto_sdk.commands.common.tools import get_remote_file, is_external_repository

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
RL = "\n"

IMPORT_API_MODULE_REGEX = r"from (\w+ApiModule) import \*(?:  # noqa: E402)?"


def build_skipped_exit_code(
    no_flake8: bool,
    no_bandit: bool,
    no_mypy: bool,
    no_pylint: bool,
    no_vulture: bool,
    no_xsoar_linter: bool,
    no_test: bool,
    no_pwsh_analyze: bool,
    no_pwsh_test: bool,
    docker_engine: bool,
) -> float:
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
    if not os.environ.get("CI"):
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


def get_test_modules(
    content_repo: GitUtil, is_external_repo: bool = is_external_repository()
) -> Dict[Path, bytes]:
    """Get required test modules from content repository - {remote}/master
    1. Tests/demistomock/demistomock.py
    2. Tests/scripts/dev_envs/pytest/conftest.py
    3. Scripts/CommonServerPython/CommonServerPython.py
    4. CommonServerUserPython.py

    Returns:
        dict: path and file content - see below modules dict
    """
    if is_external_repo:
        modules = [
            Path("demistomock.py"),
            Path("dev_envs/pytest/conftest.py"),
            Path("CommonServerPython.py"),
            Path("CommonServerUserPython.py"),
            Path("demistomock.ps1"),
            Path("CommonServerPowerShell.ps1"),
        ]
    else:
        modules = [
            Path("Tests/demistomock/demistomock.py"),
            Path("Tests/scripts/dev_envs/pytest/conftest.py"),
            Path("Packs/Base/Scripts/CommonServerPython/CommonServerPython.py"),
            Path("Tests/demistomock/demistomock.ps1"),
            Path(
                "Packs/Base/Scripts/CommonServerPowerShell/CommonServerPowerShell.ps1"
            ),
        ]
    modules_content = {}
    if content_repo:
        # Trying to get file from local repo before downloading from GitHub repo (Get it from disk), Last fetch
        module_not_found = False

        for module in modules:
            try:
                module_full_path = content_repo.repo.working_dir / module  # type: ignore
                logger.debug(f"read file {module_full_path}")
                if module.match("*CommonServerPython.py"):
                    # Remove import of DemistoClassApiModule in CommonServerPython,
                    # since tests don't use this class and the import fails the tests.
                    modules_content[module] = (
                        (module_full_path)
                        .read_bytes()
                        .replace(b"from DemistoClassApiModule import *", b"")
                    )
                    logger.debug(
                        f"Changed file {module_full_path} without demisto import"
                    )
                else:
                    modules_content[module] = (module_full_path).read_bytes()
            except FileNotFoundError:
                if module.name == "CommonServerUserPython.py":
                    logger.debug(
                        "CommonServerUserPython.py was not found, skipping as it will be created later."
                    )
                    continue
                module_not_found = True
                logger.warning(
                    f"Module {module} was not found, possibly deleted due to being in a feature branch"
                )

        if module_not_found and is_external_repo:
            raise DemistoException("Unable to find module in external repository")
    else:
        # If not succeed to get from local repo copy, Download the required modules from GitHub
        for module in modules:
            url = f"https://raw.githubusercontent.com/demisto/content/master/{module}"
            for trial in range(2):
                res = requests.get(url=url, verify=False)
                if res.ok:
                    logger.debug("got file {module} - ok - not 4XX or 5XX")
                    modules_content[module] = res.content
                    break
                elif trial == 2:
                    raise requests.exceptions.ConnectionError

    return modules_content


@contextmanager
def add_typing_module(lint_files: List[Path], python_version: str):
    """Check for typing import for python2 packages
        1. Entrance - Add import typing in the begining of the file.
        2. Closing - change back to original.

    Args:
        lint_files(list): File to execute lint - for adding typing in python 2.7
        python_version(str): The package python version.

    Raises:
        IOError: if can't write to files due permissions or other reasons
    """
    added_modules: List[Path] = []
    back_lint_files: List[Path] = []
    try:
        # Add typing import if needed to python version 2 packages
        py_ver = parse(python_version).major  # type: ignore
        if py_ver < 3:
            for lint_file in lint_files:
                data = lint_file.read_text(encoding="utf-8")
                typing_regex = "(from typing import|import typing)"
                module_match = re.search(typing_regex, data)
                if not module_match:
                    original_file = lint_file
                    back_file = lint_file.with_suffix(".bak")
                    original_file.rename(back_file)
                    data = back_file.read_text()
                    original_file.write_text(
                        "from typing import *  # noqa: F401" + "\n" + data
                    )
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
                original_name = back_file.with_suffix(".py")
                back_file.rename(original_name)


@contextmanager
def add_tmp_lint_files(
    content_repo: Path,
    pack_path: Path,
    lint_files: List[Path],
    modules: Dict[Path, bytes],
    pack_type: str,
):
    """LintFiles is context manager to mandatory files for lint and test
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
            pwsh_module = TYPE_PWSH == pack_type and module.suffix == ".ps1"
            python_module = TYPE_PYTHON == pack_type and module.suffix == ".py"
            if pwsh_module or python_module:
                copied_api_module_path = pack_path / module.name
                if not copied_api_module_path.exists():
                    copied_api_module_path.write_bytes(content)
                    added_modules.append(copied_api_module_path)
        if pack_type == TYPE_PYTHON:
            # Append empty so it will exists
            copied_common_server_python_path = pack_path / "CommonServerUserPython.py"
            if not copied_common_server_python_path.exists():
                copied_common_server_python_path.touch()
                added_modules.append(copied_common_server_python_path)

            api_modules = add_api_modules(lint_files, content_repo, pack_path)
            added_modules.extend(api_modules)

        yield
    except Exception as e:
        logger.error(f"add_tmp_lint_files unexpected exception: {str(e)}")
        raise


def add_api_modules(
    module_list: List[Path], content_repo: Path, pack_path: Path
) -> List[Path]:
    """Add API modules to directory if needed
    Args:
        modules_list(list): Modules that might import Api Modules
        content_repo(Path): Absolute path of the repository
        pack_path(Path): Absolute path of pack
    Returns:
        list[Path]: Paths of the added ApiModules
    Raises:
        IOError: if can't write to files due permissions or other reasons
    """
    added_modules: List[Path] = []
    for module in module_list:
        api_modules = re.findall(IMPORT_API_MODULE_REGEX, module.read_text())
        for module_name in api_modules:
            api_module_path = Path(
                f"Packs/ApiModules/Scripts/{module_name}/{module_name}.py"
            )
            copied_api_module_path = pack_path / f"{module_name}.py"
            if content_repo:  # if working in a repo
                module_path = content_repo / api_module_path
                shutil.copy(src=module_path, dst=copied_api_module_path)
            else:
                api_content = get_remote_file(
                    full_file_path=f"https://raw.githubusercontent.com/demisto/content/master/{api_module_path}",
                    return_content=True,
                )
                copied_api_module_path.write_bytes(api_content)

            added_modules.append(copied_api_module_path)
    # if there is added_modules - we recursively check for ApiModules imported by them
    return (
        added_modules + add_api_modules(added_modules, content_repo, pack_path)
        if added_modules
        else []
    )


def get_file_from_container(
    container_obj: Container, container_path: str, encoding: str = ""
) -> Union[str, bytes]:
    """Copy file from container.

    Args:
        container_obj(Container): Container ID to copy file from
        container_path(Path): Path in container image (file)
        encoding(str): valid encoding e.g. utf-8

    Returns:
        str or bytes: file as string decoded in utf-8

    Raises:
        IOError: Raise IO error if unable to create temp file
    """
    data: Union[str, bytes] = b""
    archive, stat = container_obj.get_archive(container_path)
    file_like = io.BytesIO(b"".join(archive))
    with tarfile.open(fileobj=file_like) as tar:
        before_read = tar.extractfile(stat["name"])
    if isinstance(before_read, io.BufferedReader):
        data = before_read.read()
    if encoding and isinstance(data, bytes):
        data = data.decode(encoding)

    return data


def copy_dir_to_container(
    container_obj: Container, host_path: Path, container_path: Path
):
    """Copy all content directory from container.

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
    with tarfile.open(fileobj=file_like_object, mode="w:gz") as archive:
        os.chdir(host_path)
        archive.add(
            ".",
            recursive=True,
            filter=lambda tarinfo: (
                tarinfo
                if not re.search(excluded_regex, Path(tarinfo.name).name)
                else None
            ),
        )
        os.chdir(old_cwd)

    for trial in range(2):
        status = container_obj.put_archive(
            path=container_path, data=file_like_object.getvalue()
        )
        if status:
            break
        elif trial == 1:
            raise docker.errors.APIError(message="unable to copy dir to container")


def stream_docker_container_output(
    streamer: Generator, logging_level: Callable = logger.info
) -> None:
    """Stream container logs

    Args:
        streamer(Generator): Generator created by docker-sdk
    """
    try:
        wrapper = textwrap.TextWrapper(
            initial_indent="\t", subsequent_indent="\t", width=150
        )
        for chunk in streamer:
            logging_level(wrapper.fill(str(chunk.decode("utf-8"))))
    except Exception:
        logger.info("Failed to stream a container log.")


@contextmanager
def pylint_plugin(dest: Path):
    """
    Function which links the given path with the content of pylint plugins folder in resources.
    The main purpose is to link each pack with the pylint plugins.
    Args:
        dest: Pack path.
    """
    plugin_dirs = Path(__file__).parent / "resources" / "pylint_plugins"

    try:
        for file in plugin_dirs.iterdir():
            if (
                file.is_file()
                and file.name != "__pycache__"
                and file.name.split(".")[1] != "pyc"
            ):
                os.symlink(file, dest / file.name)

        yield
    finally:
        for file in plugin_dirs.iterdir():
            if (
                file.is_file()
                and file.name != "__pycache__"
                and file.name.split(".")[1] != "pyc"
            ):
                if os.path.lexists(dest / f"{file.name}"):
                    (dest / f"{file.name}").unlink()


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
    output_lst = output.split("\n")
    # Warnings and errors lists currently relevant for XSOAR Linter
    warnings_list = []
    error_list = []
    # Others list is relevant for mypy and flake8.
    other_msg_list = []
    for msg in output_lst:
        # 'W:' for python2 xsoar linter
        # 'W[0-9]' for python3 xsoar linter
        if (msg.startswith("W") and msg[1].isdigit()) or "W:" in msg or "W90" in msg:
            warnings_list.append(msg)
        elif (msg.startswith("E") and msg[1].isdigit()) or "E:" in msg or "E90" in msg:
            error_list.append(msg)
        else:
            other_msg_list.append(msg)

    return error_list, warnings_list, other_msg_list


def coverage_report_editor(coverage_file, code_file_absolute_path):
    """

    Args:
        coverage_file: the .coverage file this contains the coverage data in sqlite format.
        code_file_absolute_path: the real absolute path to the measured code file.

    Notes:
        the .coverage files contain all the files list with their absolute path.
        but our tests (pytest step) are running inside a docker container.
        so we have to change the path to the correct one.
    """
    logger.info(f"Editing coverage report for {coverage_file}")
    with sqlite3.connect(coverage_file) as sql_connection:
        cursor = sql_connection.cursor()
        index = cursor.execute("SELECT count(*) FROM file").fetchall()[0][0]
        if not index == 1:
            logger.warning("unexpected file list in coverage report")
        else:
            cursor.execute(
                "UPDATE file SET path = ? WHERE id = ?", (code_file_absolute_path, 1)
            )
            sql_connection.commit()
        cursor.close()
    if not index == 1:
        Path(coverage_file).unlink()


def coverage_files():
    packs_pass = Path("Packs")
    for cov_path in packs_pass.glob("*/Integrations/*/.coverage"):
        yield str(cov_path)
    for cov_path in packs_pass.glob("*/Scripts/*/.coverage"):
        yield str(cov_path)


def generate_coverage_report(
    html=False, xml=False, report=True, cov_dir="coverage_report"
):
    """
    Args:
        html(bool): should generate an html report. default false
        xml(bool): should generate an xml report. default false
        report(bool): should print the coverage report. default true
        cov_dir(str): the directory to place the report files (.coverage, html and xml report)
    """
    cov_file = os.path.join(cov_dir, ".coverage")
    cov = coverage.Coverage(data_file=cov_file)
    cov.combine(coverage_files())
    if not Path(cov_file).exists():
        logger.warning(
            f"skipping coverage report {cov_file} file not found. "
            f"Should not expect this if code files were changed or when linting all with pytest."
        )
        return

    export_msg = "exporting {0} coverage report to {1}"
    if report:
        report_data = io.StringIO()
        report_data.write(
            "\n\n############################\n unit-tests coverage report\n############################\n"
        )
        try:
            cov.report(file=report_data)
        except coverage.misc.CoverageException as warning:
            if (
                isinstance(warning.args, tuple)
                and warning.args
                and warning.args[0] == "No data to report."
            ):
                logger.info(f"No coverage data in file {cov_file}")
                return
            raise warning
        report_data.seek(0)
        # avoid parsing % that may exist in the data
        logger.info("%s", report_data.read())

    if html:
        html_dir = os.path.join(cov_dir, "html")
        logger.info(export_msg.format("html", os.path.join(html_dir, "index.html")))
        try:
            cov.html_report(directory=html_dir)
        except coverage.misc.CoverageException as warning:
            logger.warning(str(warning))
            return
    if xml:
        xml_file = os.path.join(cov_dir, "coverage.xml")
        logger.info(export_msg.format("xml", xml_file))
        try:
            cov.xml_report(outfile=xml_file)
        except coverage.misc.CoverageException as warning:
            logger.warning(str(warning))
            return

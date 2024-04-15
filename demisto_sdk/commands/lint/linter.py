# STD python packages

import copy
import os
import platform
import re
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import docker
import docker.errors
import docker.models.containers
import git
import requests.exceptions
from packaging.version import parse
from wcmatch.pathlib import NEGATE, Path

from demisto_sdk.commands.common.constants import (
    API_MODULE_FILE_SUFFIX,
    DOCKER_REGISTRY_URL,
    FORMATTING_SCRIPT,
    INTEGRATIONS_DIR,
    NATIVE_IMAGE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PARTNER_SUPPORT,
    TESTS_REQUIRE_NETWORK_PACK_IGNORE,
    TYPE_PWSH,
    TYPE_PYTHON,
)
from demisto_sdk.commands.common.docker_helper import (
    docker_login,
    get_docker,
    get_python_version,
    init_global_docker_client,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
    get_dev_native_image,
)
from demisto_sdk.commands.common.timers import timer
from demisto_sdk.commands.common.tools import (
    get_docker_images_from_yml,
    get_file,
    get_id,
    get_pack_ignore_content,
    get_pack_name,
    get_yaml,
    run_command_os,
)
from demisto_sdk.commands.lint.commands_builder import (
    build_bandit_command,
    build_flake8_command,
    build_mypy_command,
    build_pwsh_analyze_command,
    build_pwsh_test_command,
    build_pylint_command,
    build_pytest_command,
    build_vulture_command,
    build_xsoar_linter_command,
)
from demisto_sdk.commands.lint.helpers import (
    EXIT_CODES,
    FAIL,
    RERUN,
    RL,
    SUCCESS,
    WARNING,
    add_tmp_lint_files,
    add_typing_module,
    coverage_report_editor,
    get_file_from_container,
    pylint_plugin,
    split_warnings_errors,
    stream_docker_container_output,
)

# 3-rd party packages

# Local packages


class DockerImageFlagOption(Enum):
    FROM_YML = "from-yml"
    NATIVE = "native:"
    NATIVE_DEV = "native:dev"
    NATIVE_GA = "native:ga"
    NATIVE_MAINTENANCE = "native:maintenance"
    ALL_IMAGES = "all"
    NATIVE_TARGET = "native:target"
    NATIVE_CANDIDATE = "native:candidate"


class Linter:
    """Linter used to activate lint command on single package

    Attributes:
        pack_dir(Path): Pack to run lint on.
        content_repo(Path): Git repo object of content repo.
        docker_engine(bool):  Whether docker engine detected by docker-sdk.
        docker_timeout(int): Timeout for docker requests.
        docker_image_flag(str): Indicates the desirable docker image to run lint on (default value is 'from-yml).
        all_packs (bool): Indicates whether all the packs should go through lint
    """

    def __init__(
        self,
        pack_dir: Path,
        content_repo: Path,
        docker_engine: bool,
        docker_timeout: int,
        docker_image_flag: str = DockerImageFlagOption.FROM_YML.value,
        all_packs: bool = False,
        docker_image_target: str = "",
        use_git: bool = False,
    ):
        self._content_repo = content_repo

        # For covering the case when a path file is sent instead of a directory
        self._pack_abs_dir = pack_dir if pack_dir.is_dir() else pack_dir.parent

        self._pack_name = None
        self.docker_timeout = docker_timeout
        self.docker_image_flag = docker_image_flag
        self.docker_image_target = docker_image_target
        # Docker client init
        if docker_engine:
            self._docker_client: docker.DockerClient = init_global_docker_client(  # type: ignore
                timeout=docker_timeout, log_prompt="Linter"
            )
            self._docker_hub_login = docker_login(self._docker_client)
        # Facts gathered regarding pack lint and test
        self._facts: Dict[str, Any] = {
            "images": [],
            "python_version": 0,
            "env_vars": {},
            "test": False,
            "lint_files": [],
            "support_level": None,
            "is_long_running": False,
            "lint_unittest_files": [],
            "additional_requirements": [],
            "docker_engine": docker_engine,
            "is_script": False,
            "commands": None,
        }
        # Pack lint status object - visualize it
        self._pkg_lint_status: Dict = {
            "pkg": None,
            "pack_type": None,
            "path": str(self._content_repo),
            "errors": [],
            "images": [],
            "flake8_errors": None,
            "XSOAR_linter_errors": None,
            "bandit_errors": None,
            "mypy_errors": None,
            "vulture_errors": None,
            "flake8_warnings": None,
            "XSOAR_linter_warnings": None,
            "bandit_warnings": None,
            "mypy_warnings": None,
            "vulture_warnings": None,
            "exit_code": SUCCESS,
            "warning_code": SUCCESS,
        }
        self._pack_name = None
        yml_file = self._pack_abs_dir.glob(
            [r"*.yaml", r"*.yml", r"!*unified*.yml"], flags=NEGATE
        )
        if not yml_file:
            logger.info(
                f"{self._pack_abs_dir} - Skipping no yaml file found {yml_file}"
            )
            self._pkg_lint_status["errors"].append("Unable to find yml file in package")
        else:
            try:
                self._yml_file = next(yml_file)  # type: ignore
                self._pack_name = self._yml_file.stem
                self._yml_file_content = get_yaml(self._yml_file)
            except StopIteration:
                logger.info(
                    f"{self._pack_abs_dir} - Skipping no yaml file found {yml_file}"
                )
                self._pkg_lint_status["errors"].append(
                    "Unable to find yml file in package"
                )
        self._all_packs = all_packs
        self._use_git = use_git

    def should_disable_network(self) -> bool:
        if config := get_pack_ignore_content(get_pack_name(str(self._pack_abs_dir))):
            if TESTS_REQUIRE_NETWORK_PACK_IGNORE in config.sections():
                ignored_integrations_scripts_ids = config[
                    TESTS_REQUIRE_NETWORK_PACK_IGNORE
                ]
                if get_id(self._yml_file_content) in ignored_integrations_scripts_ids:
                    return False
        return True

    @timer(group_name="lint")
    def run_pack(
        self,
        no_flake8: bool,
        no_bandit: bool,
        no_mypy: bool,
        no_pylint: bool,
        no_vulture: bool,
        no_xsoar_linter: bool,
        no_pwsh_analyze: bool,
        no_pwsh_test: bool,
        no_test: bool,
        modules: dict,
        keep_container: bool,
        test_xml: str,
        no_coverage: bool,
    ) -> dict:
        """Run lint and tests on single package
        Performing the follow:
            1. Run the lint on OS - flake8, bandit, mypy.
            2. Run in package docker - pylint, pytest.

        Args:
            no_xsoar_linter(bool): Whether to skip xsoar-linter
            no_flake8(bool): Whether to skip flake8
            no_bandit(bool): Whether to skip bandit
            no_mypy(bool): Whether to skip mypy
            no_vulture(bool): Whether to skip vulture
            no_pylint(bool): Whether to skip pylint
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            modules(dict): Mandatory modules to locate in pack path (CommonServerPython.py etc)
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            no_coverage(bool): Run pytest without coverage report

        Returns:
            dict: lint and test all status, pkg status)
        """
        # Gather information for lint check information
        log_prompt = f"{self._pack_name} - Run"
        logger.info(f"{log_prompt} - Start")
        try:
            skip = self._gather_facts(modules)
            # If not python pack - skip pack
            if skip:
                return self._pkg_lint_status
            # Locate mandatory files in pack path - for more info checkout the context manager LintFiles
            with add_tmp_lint_files(
                content_repo=self._content_repo,
                pack_path=self._pack_abs_dir,
                lint_files=self._facts["lint_files"],
                modules=modules,
                pack_type=self._pkg_lint_status["pack_type"],
            ):
                # Run lint check on host - flake8, bandit, mypy
                if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                    self._run_lint_in_host(
                        no_bandit=no_bandit,
                        no_mypy=no_mypy,
                        no_xsoar_linter=no_xsoar_linter,
                    )

                # Run lint and test check on pack docker image
                if self._facts["docker_engine"]:
                    self._run_lint_on_docker_image(
                        no_pylint=no_pylint,
                        no_test=no_test,
                        no_pwsh_analyze=no_pwsh_analyze,
                        no_pwsh_test=no_pwsh_test,
                        keep_container=keep_container,
                        test_xml=test_xml,
                        no_coverage=no_coverage,
                        no_vulture=no_vulture,
                        no_flake8=no_flake8,
                        should_disable_network=self.should_disable_network(),
                    )
        except Exception as ex:
            err = f"{self._pack_abs_dir}: Unexpected fatal exception: {str(ex)}"
            logger.error(f"{err}. Traceback: {traceback.format_exc()}")
            self._pkg_lint_status["errors"].append(err)
            self._pkg_lint_status["exit_code"] += FAIL
        logger.info(f"{log_prompt} - Finished Successfully")
        return self._pkg_lint_status

    @timer(group_name="lint")
    def _gather_facts(self, modules: dict) -> bool:
        """Gathering facts about the package - python version, docker images, valid docker image, yml parsing
        Args:
            modules(dict): Test mandatory modules to be ignore in lint check

        Returns:
            bool: Indicating if to continue further or not, if False exit Thread, Else continue.
        """
        # Looking for pkg yaml
        log_prompt = f"{self._pack_name} - Facts"
        self._pkg_lint_status["pkg"] = self._pack_name
        logger.info(f"{log_prompt} - Using yaml file {self._yml_file}")
        # Parsing pack yaml - in order to verify if check needed
        try:
            script_obj: Dict = {}
            yml_obj: Dict = YAML_Handler().load(self._yml_file)
            if not isinstance(yml_obj, dict):
                self._pkg_lint_status["errors"].append("Unable to parse package yml")
                return True
            script_obj = (
                yml_obj.get("script", {})
                if isinstance(yml_obj.get("script"), dict)
                else yml_obj
            )
            # if the script/integration is deprecated and the -a or -g flag
            if (self._all_packs or self._use_git) and yml_obj.get("deprecated"):
                logger.info(
                    f"skipping lint for {self._pack_name} because its deprecated. To lint it, use the -i flag."
                )
                return True
            self._facts["is_script"] = (
                True if "Scripts" in self._yml_file.parts else False
            )
            self._facts["is_long_running"] = script_obj.get("longRunning")
            self._facts["commands"] = self._get_commands_list(script_obj)
            self._facts["formatting_script"] = FORMATTING_SCRIPT in script_obj.get(
                "tags", []
            )
            self._pkg_lint_status["pack_type"] = script_obj.get("type")
        except (FileNotFoundError, OSError, KeyError):
            self._pkg_lint_status["errors"].append("Unable to parse package yml")
            return True
        # return no check needed if not python pack
        if self._pkg_lint_status["pack_type"] not in (TYPE_PYTHON, TYPE_PWSH):
            logger.info(
                f"{log_prompt} - Skipping due to not Python, Powershell package - Pack is"
                f" {self._pkg_lint_status['pack_type']}"
            )
            return True

        # Docker images
        yml_obj_id = (
            yml_obj.get("commonfields", {}).get("id", "")
            if isinstance(yml_obj, dict)
            else ""
        )
        if self._facts["docker_engine"]:
            logger.info(f"{log_prompt} - Collecting all docker images to pull")
            images = []
            for docker_image in self.docker_image_flag.split(","):
                temp_images = self._get_docker_images_for_lint(
                    script_obj=script_obj,
                    script_id=yml_obj_id,
                    docker_image_flag=docker_image,
                    docker_image_target=self.docker_image_target,
                )
                images.extend(temp_images)
                images = list(set(images))
            if not images:
                # If no docker images to run on - skip checks in both docker and host
                logger.info(
                    f"{log_prompt} - No docker images to run on - Skipping run lint in host as well."
                )
                return True
            self._facts["images"] = [[image, -1] for image in images]

            # we want to use DOCKER_REGISTRY_URL only if we run in content build (and not CI/CD for example)
            if os.getenv("CONTENT_GITLAB_CI", False):
                self._facts["images"] = [
                    [f"{DOCKER_REGISTRY_URL}/{image[0]}", -1]
                    for image in self._facts["images"]
                ]
            # Gather environment variables for docker execution
            self._facts["env_vars"] = {
                "CI": os.getenv("CI", False),
                "DEMISTO_LINT_UPDATE_CERTS": os.getenv(
                    "DEMISTO_LINT_UPDATE_CERTS", "yes"
                ),
                "PYTHONDONTWRITEBYTECODE": "1",
            }

        lint_files = set()
        # Facts for python pack
        if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
            self._update_support_level()
            if self._facts["docker_engine"]:
                # Getting python version from docker image - verifying if not valid docker image configured
                for image in self._facts["images"]:
                    if py_num_version := get_python_version(image=image[0]):
                        python_version_string = (
                            f"{py_num_version.major}.{py_num_version.minor}"
                        )
                    else:
                        raise ValueError(
                            f"Could not get python version from docker-image {image[0]}"
                        )

                    image[1] = python_version_string
                    logger.info(
                        f"{self._pack_name} - Facts - {image[0]} - Python {python_version_string}"
                    )
                    if not self._facts["python_version"]:
                        self._facts["python_version"] = python_version_string

                # Checking whatever *test* exists in package
                self._facts["test"] = (
                    True
                    if next(
                        self._pack_abs_dir.glob([r"test_*.py", r"*_test.py"]), None  # type: ignore
                    )
                    else False
                )
                if self._facts["test"]:
                    logger.info(f"{log_prompt} - Tests found")
                else:
                    logger.info(f"{log_prompt} - Tests not found")
                # Gather package requirements embedded in test-requirements.py file
                test_requirements = self._pack_abs_dir / "test-requirements.txt"
                if test_requirements.exists():
                    try:
                        additional_req = (
                            test_requirements.read_text(encoding="utf-8")
                            .strip()
                            .split("\n")
                        )
                        self._facts["additional_requirements"].extend(additional_req)
                        logger.info(
                            f"{log_prompt} - Additional package Pypi packages found - {additional_req}"
                        )
                    except (FileNotFoundError, OSError):
                        self._pkg_lint_status["errors"].append(
                            "Unable to parse test-requirements.txt in package"
                        )
            elif not self._facts["python_version"]:
                # get python version from yml
                pynum = (
                    "3.7"
                    if (script_obj.get("subtype", "python3") == "python3")
                    else "2.7"
                )
                self._facts["python_version"] = pynum
                logger.info(f"{log_prompt} - Using python version from yml: {pynum}")

            # Get lint files
            lint_files = set(
                self._pack_abs_dir.glob(
                    ["*.py", "!__init__.py", "!*.tmp"], flags=NEGATE
                )
            )
        # Facts for Powershell pack
        elif self._pkg_lint_status["pack_type"] == TYPE_PWSH:
            # Get lint files
            lint_files = set(
                self._pack_abs_dir.glob(
                    [
                        "*.ps1",
                        "!*Tests.ps1",
                        "CommonServerPowerShell.ps1",
                        "demistomock.ps1'",
                    ],
                    flags=NEGATE,
                )
            )

        # Add CommonServer to the lint checks
        if "commonserver" in self._pack_abs_dir.name.lower():
            # Powershell
            if self._pkg_lint_status["pack_type"] == TYPE_PWSH:
                self._facts["lint_files"] = [Path(self._pack_abs_dir / "CommonServerPowerShell.ps1")]  # type: ignore
            # Python
            elif self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                self._facts["lint_files"] = [Path(self._pack_abs_dir / "CommonServerPython.py")]  # type: ignore
        else:
            test_modules = {
                self._pack_abs_dir / module.name for module in modules.keys()
            }
            lint_files = lint_files.difference(test_modules)
            self._facts["lint_files"] = list(lint_files)

        if self._facts["lint_files"]:
            # Remove files that are in gitignore.
            self._remove_gitignore_files(log_prompt)
            for lint_file in self._facts["lint_files"]:
                logger.info(f"{log_prompt} - Lint file {lint_file}")
        else:
            logger.info(f"{log_prompt} - Lint files not found")

        if not yml_obj_id.endswith(API_MODULE_FILE_SUFFIX):
            # remove api module from lint files if the integration/script that we use is not an api module.
            self._facts["lint_files"] = [
                file
                for file in self._facts["lint_files"]
                if API_MODULE_FILE_SUFFIX not in file.name
            ]

        self._split_lint_files()

        self._linter_to_commands()

        return False

    def _linter_to_commands(self):
        self._facts["lint_to_commands"] = {
            "pylint": build_pylint_command(
                self._facts["lint_files"],
                docker_version=self._facts.get("python_version"),
            ),
            "flake8": build_flake8_command(
                self._facts["lint_files"] + self._facts["lint_unittest_files"]
            ),
            "vulture": build_vulture_command(
                self._facts["lint_files"], self._pack_abs_dir
            ),
        }

    def _remove_gitignore_files(self, log_prompt: str) -> None:
        """
        Skipping files that matches gitignore patterns.
        Args:
            log_prompt(str): log prompt string

        Returns:

        """
        try:
            repo = GitUtil(self._content_repo).repo
            files_to_ignore = repo.ignored(self._facts["lint_files"])
            for file in files_to_ignore:
                logger.info(f"{log_prompt} - Skipping gitignore file {file}")
            self._facts["lint_files"] = [
                path
                for path in self._facts["lint_files"]
                if path not in files_to_ignore
            ]

        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            logger.debug("No gitignore files is available")

    def _split_lint_files(self):
        """Remove unit test files from _facts['lint_files'] and put into their own list _facts['lint_unittest_files']
        This is because not all lints should be done on unittest files.
        """
        lint_files_list = copy.deepcopy(self._facts["lint_files"])
        for lint_file in lint_files_list:
            if lint_file.name.startswith("test_") or lint_file.name.endswith(
                "_test.py"
            ):
                self._facts["lint_unittest_files"].append(lint_file)
                self._facts["lint_files"].remove(lint_file)

    @timer(group_name="lint")
    def _run_lint_in_host(self, no_bandit: bool, no_mypy: bool, no_xsoar_linter: bool):
        """Run lint check on host

        Args:
            no_flake8(bool): Whether to skip flake8.
            no_bandit(bool): Whether to skip bandit.
            no_mypy(bool): Whether to skip mypy.
            no_vulture(bool): Whether to skip Vulture.
        """
        log_prompt = f"{self._pack_name} - Run Lint In Host"
        logger.info(f"{log_prompt} - Started")
        exit_code: int = SUCCESS
        for lint_check in ["XSOAR_linter", "bandit", "mypy"]:
            exit_code = SUCCESS
            output = ""
            if self._facts["lint_files"]:
                if lint_check == "XSOAR_linter" and not no_xsoar_linter:
                    exit_code, output = self._run_xsoar_linter(
                        py_num=self._facts["python_version"],
                        lint_files=self._facts["lint_files"],
                    )
                elif lint_check == "bandit" and not no_bandit:
                    exit_code, output = self._run_bandit(
                        lint_files=self._facts["lint_files"]
                    )

                elif (
                    lint_check == "mypy"
                    and not no_mypy
                    and parse(self._facts["python_version"]).major >= 3  # type: ignore[union-attr]
                ):
                    # mypy does not support python2 now
                    exit_code, output = self._run_mypy(
                        py_num=self._facts["python_version"],
                        lint_files=self._facts["lint_files"],
                    )

            self._handle_lint_results(exit_code, lint_check, output)
        logger.info(f"{log_prompt} - Finished successfully")

    def _handle_lint_results(self, exit_code, lint_check, output):
        # check for any exit code other than 0
        if exit_code:
            error, warning, other = split_warnings_errors(output)
        if exit_code and warning:
            self._pkg_lint_status["warning_code"] |= EXIT_CODES[lint_check]
            self._pkg_lint_status[f"{lint_check}_warnings"] = "\n".join(warning)
        if exit_code & FAIL:
            self._pkg_lint_status["exit_code"] |= EXIT_CODES[lint_check]
            # if the error were extracted correctly as they start with E
            if error:
                self._pkg_lint_status[f"{lint_check}_errors"] = "\n".join(error)
                # if there were errors but they do not start with E
            else:
                self._pkg_lint_status[f"{lint_check}_errors"] = "\n".join(other)

    @timer(group_name="lint")
    def _run_xsoar_linter(self, py_num: str, lint_files: List[Path]) -> Tuple[int, str]:
        """Runs Xsaor linter in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Xsoar linter errors
        """
        status = SUCCESS
        FAIL_PYLINT = 0b10
        with pylint_plugin(self._pack_abs_dir):
            log_prompt = f"{self._pack_name} - XSOAR Linter"
            logger.info(f"{log_prompt} - Start")
            myenv = os.environ.copy()
            if myenv.get("PYTHONPATH"):
                myenv["PYTHONPATH"] += ":" + str(self._pack_abs_dir)
            else:
                myenv["PYTHONPATH"] = str(self._pack_abs_dir)
            if self._facts["is_long_running"]:
                myenv["LONGRUNNING"] = "True"

            py_ver = parse(py_num).major  # type: ignore
            if py_ver < 3:
                myenv["PY2"] = "True"
            myenv["is_script"] = str(self._facts["is_script"])
            # as Xsoar checker is a pylint plugin and runs as part of pylint code, we can not pass args to it.
            # as a result we can use the env vars as a getway.
            myenv["commands"] = (
                ",".join([str(elem) for elem in self._facts["commands"]])
                if self._facts["commands"]
                else ""
            )
            stdout, stderr, exit_code = run_command_os(
                command=build_xsoar_linter_command(
                    files=lint_files,  # type: ignore
                    support_level=self._facts.get("support_level", "base"),
                    formatting_script=self._facts.get("formatting_script", False),
                ),
                cwd=self._pack_abs_dir,
                env=myenv,
            )
        if exit_code & FAIL_PYLINT:
            logger.error(f"{log_prompt} - Finished, errors found")
            status = FAIL
        if exit_code & WARNING:
            logger.warning(f"{log_prompt} - Finished, warnings found")
            if not status:
                status = WARNING
        # if pylint did not run and failure exit code has been returned from run commnad
        elif exit_code & FAIL:
            status = FAIL
            logger.debug(f"{log_prompt} - Actual XSOAR linter error -")
            logger.debug(
                f"{log_prompt} - Full format stdout: {RL if stdout else ''}{stdout}"
            )
            # for contrib prs which are not merged from master and do not have pylint in dev-requirements-py2.
            if os.environ.get("CI"):
                stdout = "Xsoar linter could not run, Please merge from master"
            else:
                stdout = (
                    "Xsoar linter could not run, please make sure you have"
                    " the necessary Pylint version for both py2 and py3"
                )
            logger.error(f"{log_prompt} - Finished, errors found")

        logger.debug(f"{log_prompt} - Finished, exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished, stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished, stderr: {RL if stderr else ''}{stderr}")

        if not exit_code:
            logger.info(f"{log_prompt} - Successfully finished")

        return status, stdout

    @timer(group_name="lint")
    def _run_bandit(self, lint_files: List[Path]) -> Tuple[int, str]:
        """Run bandit in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Bandit"
        logger.info(f"{log_prompt} - Start")
        stdout, stderr, exit_code = run_command_os(
            command=build_bandit_command(lint_files),  # type: ignore
            cwd=self._pack_abs_dir,
        )
        logger.debug(f"{log_prompt} - Finished, exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished, stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished, stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.error(f"{log_prompt} - Finished, errors found")
            if stderr:
                return FAIL, stderr
            else:
                return FAIL, stdout

        logger.info(f"{log_prompt} - Successfully finished")

        return SUCCESS, ""

    @timer(group_name="lint")
    def _run_mypy(self, py_num: str, lint_files: List[Path]) -> Tuple[int, str]:
        """Run mypy in pack dir

        Args:
            py_num(str): The python version in use
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Mypy"
        logger.info(f"{log_prompt} - Start")
        with add_typing_module(lint_files=lint_files, python_version=py_num):  # type: ignore
            mypy_command = build_mypy_command(
                files=lint_files, version=py_num, content_repo=self._content_repo  # type: ignore
            )
            stdout, stderr, exit_code = run_command_os(
                command=mypy_command, cwd=self._pack_abs_dir
            )
        logger.debug(f"{log_prompt} - Finished, exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished, stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished, stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.error(f"{log_prompt} - Finished, errors found")
            if stderr:
                return FAIL, stderr
            else:
                return FAIL, stdout

        logger.info(f"{log_prompt} - Successfully finished")

        return SUCCESS, ""

    @timer(group_name="lint")
    def _run_lint_on_docker_image(
        self,
        no_pylint: bool,
        no_test: bool,
        no_pwsh_analyze: bool,
        no_pwsh_test: bool,
        keep_container: bool,
        test_xml: str,
        no_coverage: bool,
        no_flake8: bool,
        no_vulture: bool,
        should_disable_network: bool,
    ):
        """Run lint check on docker image

        Args:
            no_pylint(bool): Whether to skip pylint
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            no_coverage(bool): Run pytest without coverage report
            should_disable_network(bool): whether network should not be disabled when running pytest, True to disable, False otherwise.

        """
        log_prompt = f"{self._pack_name} - Run Lint On Docker Image"
        if self._facts["images"]:
            logger.info(
                f'{log_prompt} - Running lint: Number of images={self._facts["images"]}'
            )
        else:
            logger.info(f"{log_prompt} - Skipped")
        for image in self._facts["images"]:
            logger.info(f"{log_prompt} - Running lint on docker image {image[0]}")
            # Docker image status - visualize
            status = {
                "image": image[0],
                "image_errors": "",
                "pylint_errors": "",
                "pytest_errors": "",
                "pytest_json": {},
                "pwsh_analyze_errors": "",
                "pwsh_test_errors": "",
            }
            # Creating image if pylint specified or found tests and tests specified
            image_id = ""
            errors = ""
            for trial in range(2):
                image_id, errors = self._docker_image_create(docker_base_image=image)
                if not errors:
                    break

            if image_id and not errors:
                # Set image creation status
                for check in [
                    "pylint",
                    "pytest",
                    "pwsh_analyze",
                    "pwsh_test",
                    "flake8",
                    "vulture",
                ]:
                    exit_code = SUCCESS
                    output = ""
                    for trial in range(2):
                        if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                            if (
                                not no_flake8
                                and check == "flake8"
                                and (
                                    self._facts["lint_files"]
                                    or self._facts["lint_unittest_files"]
                                )
                            ):
                                exit_code, output = self._docker_run_linter(
                                    linter=check,
                                    test_image=image_id,
                                    keep_container=keep_container,
                                )
                            if (
                                not no_vulture
                                and check == "vulture"
                                and self._facts["lint_files"]
                            ):
                                exit_code, output = self._docker_run_linter(
                                    linter=check,
                                    test_image=image_id,
                                    keep_container=keep_container,
                                )
                            # Perform pylint
                            if (
                                not no_pylint
                                and check == "pylint"
                                and self._facts["lint_files"]
                            ):
                                exit_code, output = self._docker_run_linter(
                                    linter=check,
                                    test_image=image_id,
                                    keep_container=keep_container,
                                )
                            # Perform pytest
                            elif (
                                not no_test
                                and self._facts["test"]
                                and check == "pytest"
                            ):
                                exit_code, output, test_json = self._docker_run_pytest(
                                    test_image=image_id,
                                    keep_container=keep_container,
                                    test_xml=test_xml,
                                    no_coverage=no_coverage,
                                    should_disable_network=should_disable_network,
                                )
                                status["pytest_json"] = test_json
                        elif self._pkg_lint_status["pack_type"] == TYPE_PWSH:
                            # Perform powershell analyze
                            if (
                                not no_pwsh_analyze
                                and check == "pwsh_analyze"
                                and self._facts["lint_files"]
                            ):
                                exit_code, output = self._docker_run_pwsh_analyze(
                                    test_image=image_id, keep_container=keep_container
                                )
                            # Perform powershell test
                            elif not no_pwsh_test and check == "pwsh_test":
                                exit_code, output = self._docker_run_pwsh_test(
                                    test_image=image_id, keep_container=keep_container
                                )
                        # If lint check perform and failed on reason related to environment will run twice,
                        # But it failing in second time it will count as test failure.
                        if (
                            (exit_code == RERUN and trial == 1)
                            or exit_code == FAIL
                            or exit_code == SUCCESS
                        ):
                            if exit_code in [RERUN, FAIL]:
                                if check in {"flake8", "vulture"}:
                                    self._handle_lint_results(exit_code, check, output)
                                else:
                                    self._pkg_lint_status["exit_code"] |= EXIT_CODES[
                                        check
                                    ]
                                    status[f"{check}_errors"] = output
                            break
            else:
                status["image_errors"] = str(errors)
                self._pkg_lint_status["exit_code"] += EXIT_CODES["image"]
            # Add image status to images
            self._pkg_lint_status["images"].append(status)
            logger.info(f"{log_prompt} - Finished linting on docker image {image[0]}")

        if self._facts["images"]:
            logger.info(
                f'{log_prompt} - Finished linting. Number of images={self._facts["images"]}'
            )

    @timer(group_name="lint")
    def _docker_image_create(self, docker_base_image: List[Any]) -> Tuple[str, str]:
        """Create docker image:
            1. Installing 'build base' if required in alpine images version - https://wiki.alpinelinux.org/wiki/GCC
            2. Installing pypi packs - if only pylint required - only pylint installed otherwise all pytest and pylint
               installed, packages which being install can be found in path demisto_sdk/commands/lint/dev_envs
            3. The docker image build done by Dockerfile template located in
                demisto_sdk/commands/lint/templates/dockerfile.jinja2

        Args:
            docker_base_image(list): docker image to use as base for installing dev deps and python version.

        Returns:
            str, str. image name to use and errors string.
        """
        log_prompt = f"{self._pack_name} - Image create"
        docker_base = get_docker()
        # Get requirements file for image
        py_ver = None
        if docker_base_image[1] != -1:
            py_ver = parse(docker_base_image[1]).major  # type: ignore
        test_image_name, errors = docker_base.get_or_create_test_image(
            docker_base_image[0],
            additional_requirements=self._facts["additional_requirements"],
            container_type=self._pkg_lint_status["pack_type"],
            log_prompt=log_prompt,
            python_version=py_ver,
            push=self._docker_hub_login,
        )
        return test_image_name, errors

    def _docker_remove_container(self, container_name: str):
        try:
            logger.info(f"Trying to remove container {container_name}")
            container = self._docker_client.containers.get(container_name)
            logger.info(f"Found container {container_name=}, {container.id=}")
            container.remove(force=True)
            logger.info(f"Successfully removed container {container_name}")
        except docker.errors.NotFound:
            logger.info(f"Didn't remove container {container_name} as it wasn't found")
            pass
        except requests.exceptions.ChunkedEncodingError as err:
            # see: https://github.com/docker/docker-py/issues/2696#issuecomment-721322548
            system_is_not_darwin = platform.system() != "Darwin"
            not_connetion_broken = "Connection broken" not in str(err)
            logger.info(
                f"Didn't remove container {container_name} as it wasn't found, {system_is_not_darwin=}, {not_connetion_broken=}"
            )
            if system_is_not_darwin or not_connetion_broken:
                raise
        except Exception:
            logger.exception(
                f"Exception when trying to remove the container {container_name}.",
                exc_info=True,
            )
            raise

    def get_container_name(self, run_type, image_name):
        # Get rid of chars that are not suitable for container names
        image_cont_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", image_name.split("/")[-1])
        image_cont_name = re.sub(r"^[^a-zA-Z0-9]", "", image_cont_name)
        return f"{self._pack_name}-{run_type}-{image_cont_name}"

    def _docker_run_linter(
        self, linter: str, test_image: str, keep_container: bool
    ) -> Tuple[int, str]:
        log_prompt = f"{self._pack_name} - {linter} - Image {test_image}"
        logger.info(f"{log_prompt} - Start")

        container_name = self.get_container_name(linter, test_image)
        # Check if previous run left container a live if it do, we remove it
        self._docker_remove_container(container_name)

        # Run container
        exit_code = SUCCESS
        output = ""
        command = [self._facts["lint_to_commands"][linter]]
        try:
            container: docker.models.containers.Container = (
                get_docker().create_container(
                    name=container_name,
                    image=test_image,
                    command=command,
                    user=f"{os.getuid()}:4000",
                    files_to_push=[(self._pack_abs_dir, "/devwork")],
                    environment=self._facts["env_vars"],
                )
            )
        except Exception:
            logger.exception(
                f"{log_prompt} - could not create container: {container_name=}, {test_image=}, {command=}"
            )
            raise
        try:
            container.start()
            stream_docker_container_output(container.logs(stream=True))
            # wait for container to finish
            container_status = container.wait()
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container.logs().decode("utf-8")
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code in [1, 2, 127]:
                # 1-fatal message issued
                # 2-Error message issued
                # 127-Command failure (for instance the linter is not exists)
                exit_code = FAIL
                output = container_log
                logger.error(f"{log_prompt} - Finished, errors found")
            elif container_exit_code in [4, 8, 16]:
                # 4-Warning message issued
                # 8-refactor message issued
                # 16-convention message issued
                logger.info(f"{log_prompt} - Successfully finished - warnings found")
                exit_code = SUCCESS
            elif container_exit_code == 32:
                # 32-usage error
                logger.critical(f"{log_prompt} - Finished - Usage error")
                exit_code = RERUN
            else:
                logger.info(f"{log_prompt} - Successfully finished")
        except Exception as e:
            logger.exception(f"{log_prompt} - Unable to run {linter}")
            exit_code = RERUN
            output = str(e)
        finally:
            # Keeping container if needed or remove it
            if keep_container:
                logger.info(f"{log_prompt} - container name {container_name}")
                container.commit(repository=container_name.lower(), tag=linter)
            else:
                try:
                    container.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        return exit_code, output

    @timer(group_name="lint")
    def _docker_run_pytest(
        self,
        test_image: str,
        keep_container: bool,
        test_xml: str,
        no_coverage: bool = False,
        should_disable_network: bool = False,
    ) -> Tuple[int, str, dict]:
        """Run Pytest in created test image

        Args:
            test_image(str): Test image id/name
            keep_container(bool): True if to keep container after execution finished
            test_xml(str): Xml saving path
            no_coverage(bool): Run pytest without coverage report
        Returns:
            int: 0 on successful, errors 1, need to retry 2
            str: Unit test json report
        """
        network_status = "disabled" if should_disable_network else "enabled"

        log_prompt = f"{self._pack_name} - Pytest - Image {test_image}, network: {network_status}"
        logger.info(f"{log_prompt} - Start")
        container_name = self.get_container_name("pytest", test_image)
        # Check if previous run left container a live if it does, Remove it
        self._docker_remove_container(container_name)
        # Collect tests
        exit_code = SUCCESS
        output = ""
        test_json = {}
        try:
            # Running pytest container
            cov_file_path = Path.joinpath(self._pack_abs_dir, ".coverage")
            cov = self._pack_abs_dir.stem if not no_coverage else ""
            uid = os.getuid() or 4000
            logger.debug(
                f"{log_prompt} - user uid for running lint/test: {uid}"
            )  # lgtm[py/clear-text-logging-sensitive-data]
            container: docker.models.containers.Container = (
                get_docker().create_container(
                    name=container_name,
                    image=test_image,
                    command=[
                        build_pytest_command(test_xml=test_xml, json=True, cov=cov)
                    ],
                    user=f"{uid}:4000",
                    files_to_push=[(self._pack_abs_dir, "/devwork")],
                    environment=self._facts["env_vars"],
                    network_disabled=should_disable_network,
                )
            )
            container.start()
            stream_docker_container_output(container.logs(stream=True))
            # Waiting for container to be finished
            container_status: dict = container.wait()
            # Getting container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code in [0, 1, 2, 5]:
                # 0-All tests passed
                # 1-Tests were collected and run but some of the tests failed
                # 2-Test execution was interrupted by the user
                # 5-No tests were collected

                if test_xml:
                    test_data_xml = get_file_from_container(
                        container_obj=container,
                        container_path="/devwork/report_pytest.xml",
                    )
                    xml_apth = Path(test_xml) / f"{self._pack_name}_pytest.xml"

                    with open(file=xml_apth, mode="bw") as f:
                        f.write(test_data_xml)  # type: ignore

                if cov:
                    cov_data = get_file_from_container(
                        container_obj=container, container_path="/devwork/.coverage"
                    )
                    cov_data = (
                        cov_data if isinstance(cov_data, bytes) else cov_data.encode()
                    )
                    with open(cov_file_path, "wb") as coverage_file:
                        coverage_file.write(cov_data)
                    coverage_report_editor(
                        cov_file_path,
                        os.path.join(
                            self._pack_abs_dir, f"{self._pack_abs_dir.stem}.py"
                        ),
                    )

                test_json = json.loads(
                    get_file_from_container(
                        container_obj=container,
                        container_path="/devwork/report_pytest.json",
                        encoding="utf-8",
                    )
                )
                for test in test_json.get("report", {}).get("tests"):
                    if test.get("call", {}).get("longrepr"):
                        test["call"]["longrepr"] = test["call"]["longrepr"].split("\n")
                if container_exit_code in [0, 5]:
                    logger.info(f"{log_prompt} - Successfully finished")
                    exit_code = SUCCESS
                elif container_exit_code in [2]:
                    output = container.logs().decode("utf-8")
                    exit_code = FAIL
                else:
                    logger.error(f"{log_prompt} - Finished, errors found")
                    exit_code = FAIL
            elif container_exit_code in [3, 4]:
                # 3-Internal error happened while executing tests
                # 4-pytest command line usage error
                logger.critical(f"{log_prompt} - Usage error")
                exit_code = RERUN
                output = container.logs().decode("utf-8")
            else:
                # Any other container exit code
                logger.error(
                    f"{log_prompt} - Finished, docker container error found ({container_exit_code})"
                )
                exit_code = FAIL
            # Remove container if not needed
            if keep_container:
                logger.info(f"{log_prompt} - Container name {container_name}")
                container.commit(repository=container_name.lower(), tag="pytest")
            else:
                try:
                    container.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to remove container {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{log_prompt} - Unable to run pytest container {e}")
            exit_code = RERUN
        logger.info(f"{self._pack_name} - Pytest finished image {test_image}")
        return exit_code, output, test_json

    def _docker_run_pwsh_analyze(
        self, test_image: str, keep_container: bool
    ) -> Tuple[int, str]:
        """Run Powershell code analyze in created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after excution finished

        Returns:
            int: 0 on successful, errors 1, need to retry 2
            str: Container log
        """
        log_prompt = f"{self._pack_name} - Powershell analyze - Image {test_image}"
        logger.info(f"{log_prompt} - Start")
        container_name = self.get_container_name("pwsh-analyze", test_image)
        # Check if previous run left container a live if it do, we remove it
        container: docker.models.containers.Container
        try:
            container = self._docker_client.containers.get(container_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Run container
        exit_code = SUCCESS
        output = ""
        try:
            uid = os.getuid() or 4000
            logger.debug(
                f"{log_prompt} - user uid for running lint/test: {uid}"
            )  # lgtm[py/clear-text-logging-sensitive-data]
            container = get_docker().create_container(
                name=container_name,
                image=test_image,
                user=f"{uid}:4000",
                environment=self._facts["env_vars"],
                files_to_push=[(self._pack_abs_dir, "/devwork")],
                command=build_pwsh_analyze_command(self._facts["lint_files"][0]),
            )
            container.start()
            stream_docker_container_output(container.logs(stream=True))
            # wait for container to finish
            container_status = container.wait()
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container.logs().decode("utf-8")
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code:
                # 1-fatal message issued
                # 2-Error message issued
                logger.error(f"{log_prompt} - Finished, errors found")
                output = container_log
                exit_code = FAIL
            else:
                logger.info(f"{log_prompt} - Successfully finished")
            # Keeping container if needed or remove it
            if keep_container:
                logger.info(f"{log_prompt} - container name {container_name}")
                container.commit(repository=container_name.lower(), tag="pwsh_analyze")
            else:
                try:
                    container.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        except (
            docker.errors.ImageNotFound,
            docker.errors.APIError,
            requests.exceptions.ReadTimeout,
        ) as e:
            logger.critical(f"{log_prompt} - Unable to run powershell test - {e}")
            exit_code = RERUN

        return exit_code, output

    def _update_support_level(self):
        logger.debug(f"Updating support level for {self._pack_name}")
        pack_dir = (
            self._pack_abs_dir.parent
            if self._pack_abs_dir.parts[-1] == INTEGRATIONS_DIR
            else self._pack_abs_dir.parent.parent
        )
        pack_metadata_file = pack_dir / PACKS_PACK_META_FILE_NAME
        logger.debug(f"Before reading content of {pack_metadata_file}")
        pack_meta_content: Dict = get_file(pack_metadata_file, raise_on_error=True)

        logger.debug(f"After reading content of {pack_metadata_file}")
        self._facts["support_level"] = pack_meta_content.get("support")
        if self._facts["support_level"] == PARTNER_SUPPORT and pack_meta_content.get(
            "Certification"
        ):
            self._facts["support_level"] = "certified partner"

    def _docker_run_pwsh_test(
        self, test_image: str, keep_container: bool
    ) -> Tuple[int, str]:
        """Run Powershell tests in created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after excution finished

        Returns:
            int: 0 on successful, errors 1, neet to retry 2
            str: Container log
        """
        log_prompt = f"{self._pack_name} - Powershell test - Image {test_image}"
        logger.info(f"{log_prompt} - Start")
        container_name = self.get_container_name("pwsh-test", test_image)
        # Check if previous run left container a live if it do, we remove it
        self._docker_remove_container(container_name)

        # Run container
        exit_code = SUCCESS
        output = ""
        try:
            uid = os.getuid() or 4000
            logger.debug(
                f"{log_prompt} - user uid for running lint/test: {uid}"
            )  # lgtm[py/clear-text-logging-sensitive-data]
            container: docker.models.containers.Container = (
                get_docker().create_container(
                    files_to_push=[(self._pack_abs_dir, "/devwork")],
                    name=container_name,
                    image=test_image,
                    command=build_pwsh_test_command(),
                    user=f"{uid}:4000",
                    environment=self._facts["env_vars"],
                )
            )
            container.start()
            stream_docker_container_output(container.logs(stream=True))
            # wait for container to finish
            container_status = container.wait()
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container.logs().decode("utf-8")
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code:
                # 1-fatal message issued
                # 2-Error message issued
                logger.error(f"{log_prompt} - Finished, errors found")
                output = container_log
                exit_code = FAIL
            else:
                logger.info(f"{log_prompt} - Successfully finished")
            # Keeping container if needed or remove it
            if keep_container:
                logger.info(f"{log_prompt} - container name {container_name}")
                container.commit(repository=container_name.lower(), tag="pwsh_test")
            else:
                try:
                    container.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        except (
            docker.errors.ImageNotFound,
            docker.errors.APIError,
            requests.exceptions.ReadTimeout,
        ) as e:
            logger.critical(f"{log_prompt} - Unable to run powershell test - {e}")
            exit_code = RERUN

        return exit_code, output

    def _get_commands_list(self, script_obj: dict):
        """Get all commands from yml file of the pack
        Args:
            script_obj(dict): the script section of the yml file.
        Returns:
            list: list of all commands
        """
        commands_list = []
        try:
            commands_obj = script_obj.get("commands", {})
            for command in commands_obj:
                commands_list.append(command.get("name", ""))
        except Exception:
            logger.debug("Failed getting the commands from the yml file")
        return commands_list

    def _is_native_image_support_script(
        self,
        native_image: str,
        supported_native_images: Set[str],
        script_id: str,
    ) -> bool:
        """
        Gets a native image name (flag) and checks if it supports the integration/script that lint runs on.

        Args:
            native_image (str): Name of the Native image to run on.
            supported_native_images (set): A set including the names of the native images that support the
                                           script/integration that lint runs on.
            script_id (str): The ID of the integration/script that lint runs on.
        Returns (bool): True - if the native image supports the integration/script that lint runs on.
                        False - Otherwise.
        """
        if native_image not in supported_native_images:
            # Integration/Script isn't supported by the requested native image
            logger.info(
                f"{script_id} - Skipping checks on docker for {native_image} - {script_id} is not supported by the "
                f"requested native image: {native_image}"
            )
            return False

        return True

    def _check_native_image_flag(self, docker_image_flag):
        """
        Gets a native docker image flag and verify that it is one of the following: 'native:ga', 'native:maintenance',
        'native:dev' or 'native:target'.
        If it isn't, raises a suitable exception.
        Args:
            docker_image_flag (str): Requested docker image flag.
        Returns (None): None
        """

        if docker_image_flag not in (
            DockerImageFlagOption.NATIVE_DEV.value,
            DockerImageFlagOption.NATIVE_GA.value,
            DockerImageFlagOption.NATIVE_MAINTENANCE.value,
            DockerImageFlagOption.NATIVE_TARGET.value,
            DockerImageFlagOption.NATIVE_CANDIDATE.value,
        ):
            err_msg = (
                f"The requested native image: '{docker_image_flag}' is not supported. The possible options are: "
                f"'native:ga', 'native:maintenance', 'native:dev' and 'native:target'. For supported native image"
                f" versions please see: 'Tests/{NATIVE_IMAGE_FILE_NAME}'"
            )
            logger.error(
                f"Skipping checks on docker for '{docker_image_flag}' - {err_msg}"
            )
            raise ValueError(err_msg)

    def _get_native_image_name_from_config_file(
        self,
        docker_image_flag: str,
    ) -> Union[str, None]:
        """
        Gets a native docker image flag and returns its mapped native image name from the
        'docker_native_image_config.json' file.

        If the requested docker image flag doesn't have a mapped native image in the config file - write to the logs.

        Args:
            docker_image_flag (str): Requested docker image flag.
        Returns (None): None
        """
        native_image_config = NativeImageConfig.get_instance()
        # parsed docker_native_image_config.json file (a singleton obj)

        if native_image := native_image_config.flags_versions_mapping.get(
            docker_image_flag
        ):
            return native_image

        else:
            # The requested native image doesn't exist in the native config file
            logger.info(
                f"Skipping checks on docker for '{docker_image_flag}' - The requested native image: "
                f"'{docker_image_flag}' is not supported. For supported native image versions please see:"
                f" 'Tests/{NATIVE_IMAGE_FILE_NAME}'"
            )
            return None

    def _get_versioned_native_image(
        self,
        native_image: str,
    ) -> Union[str, None]:
        """
        Gets a versioned native image name, and finds it's reference (tag) in the docker_native_image_config.json file.
        Args:
            native_image (str): Name of the Native image to run on.
        Returns (str): The native image reference (tag).
        """
        logger.info(
            f"{self._pack_name} - Get Versioned Native Image - {native_image} - Started"
        )

        native_image_config = NativeImageConfig.get_instance()
        # parsed docker_native_image_config.json file (a singleton obj)

        return native_image_config.get_native_image_reference(native_image)

    def _get_all_docker_images(
        self,
        script_obj: Dict,
        script_id: str,
        supported_native_images: Set[str],
    ) -> List[str]:
        """
        Gets the following docker images references:
            1. Native GA - the native image of the current server version.
            2. Native Maintenance - the native image of the previous server version.
            3. Native Dev - The latest tag of the native image for Docker Hub.
            4. The docker images that appear in the YML file of the integration/script that lint runs on.
        Args:
            script_obj (Dict): A yml as dict of the integration/script that lint runs on.
            script_id (str): The ID of the integration/script that lint runs on.
            supported_native_images (set): A set including the names of the native images supported for the
                                           script/integration that lint runs on.
        Returns (List): A list including all the docker images to run on.
        """
        logger.info(f"{self._pack_name} - Get All Docker Images Started")

        # Get docker images from yml:
        logger.info(f"{self._pack_name} - Get Docker Image from YML - Started")
        imgs = get_docker_images_from_yml(script_obj)

        # Get native images:
        native_image_config = NativeImageConfig.get_instance()
        # parsed docker_native_image_config.json file (a singleton obj)

        for native_image in native_image_config.native_images:
            if self._is_native_image_support_script(
                native_image, supported_native_images, script_id
            ):
                # When running lint --di all, do not run native:dev
                if native_image != DockerImageFlagOption.NATIVE_DEV.value:
                    native_image_ref = self._get_versioned_native_image(native_image)
                    if native_image_ref:
                        imgs.append(native_image_ref)

        return imgs

    def _get_docker_images_for_lint(
        self,
        script_obj: Dict,
        script_id: str,
        docker_image_flag: str,
        docker_image_target: Optional[str],
    ) -> List[str]:
        """Gets a yml as dict of the current integration/script that lint runs on, and a flag indicates on which docker
         images lint should run.
         Creates a list including all the desirable docker images according to the following logic:
            - If docker_image_flag is 'native:ga', lint will run on the native image of the ga server version.

            - If docker_image_flag is 'native:maintenance', lint will run on the native image of the previous
              server version.

            - If docker_image_flag is 'native:dev', lint will find the latest tag of the native image (in Docker Hub)
              and will run on it.

            ** If the integration/script that lint runs on not support the requested native image - the checks on
               docker and in host will be skipped.

            - If docker_image_flag is 'from-yml', lint will run on the docker images appearing in the YML file of the
              integration/script.

            - If docker_image_flag is 'all', lint will run on:
                1. Native GA - the native image of the current server version.
                2. Native Maintenance - the native image of the previous server version.
                3. Native Candidate - the candidate of the next GA version (the last dev version that was checked).
                4. The docker images that appear in the YML file of the integration/script that lint runs on.

            - If the docker_image_flag is a specific docker image tag, lint will try to run on it.
        Args:
            script_obj (dict): A yml dict of the integration/script that lint runs on.
            script_id (str): The ID of the integration/script that lint runs on.
            docker_image_flag (str): A flag indicates on which docker images lint should run.
            docker_image_target (Optional[str]): The docker image to test native supported content on.
                                       Must be used with docker_image_flag native-target
        Returns:
            List. A list of all desirable docker images references.
        """
        log_prompt = f"{self._pack_name} - Get All Docker Images For Lint"
        logger.info(
            f"{log_prompt} - Requested docker image flag is: '{docker_image_flag}'"
        )
        imgs = []

        if (
            docker_image_flag == DockerImageFlagOption.FROM_YML.value
        ):  # the default option
            # Desirable docker images are the docker images from the yml file (alt-dockerimages included)
            logger.info(f"{self._pack_name} - Get Docker Image from YML - Started")
            if imgs := get_docker_images_from_yml(script_obj):
                logger.info(
                    f"{log_prompt} - Docker images to run on are: {', '.join(imgs)}"
                )
            return imgs

        di_from_yml = script_obj.get("dockerimage")
        # If the 'dockerimage' key does not exist in yml - run on native image checks will be skipped
        native_image_config = NativeImageConfig.get_instance()
        # parsed docker_native_image_config.json file (a singleton obj)
        supported_native_images_obj = ScriptIntegrationSupportedNativeImages(
            _id=script_id,
            native_image_config=native_image_config,
            docker_image=di_from_yml,
        )
        supported_native_images = set(
            supported_native_images_obj.get_supported_native_image_versions(
                only_production_tags=False
            )
        )

        if docker_image_flag.startswith(DockerImageFlagOption.NATIVE.value):
            # Desirable docker image to run on is a native image

            self._check_native_image_flag(docker_image_flag)

            image_support = docker_image_flag
            if docker_image_flag == DockerImageFlagOption.NATIVE_TARGET.value:
                image_support = DockerImageFlagOption.NATIVE_DEV.value

            if native_image := self._get_native_image_name_from_config_file(
                image_support
            ):
                if self._is_native_image_support_script(
                    native_image, supported_native_images, script_id
                ):  # Integration/Script is supported by the requested native image
                    native_image_ref: Optional[str] = ""

                    if (
                        docker_image_flag == DockerImageFlagOption.NATIVE_TARGET.value
                        and docker_image_target
                    ):
                        # Desirable docker image to run is the target image only on native supported content.
                        native_image_ref = docker_image_target

                    elif docker_image_flag == DockerImageFlagOption.NATIVE_DEV.value:
                        # Desirable docker image to run on is the dev native image - get the latest tag from Docker Hub
                        native_image_ref = get_dev_native_image()

                    else:
                        # Desirable docker image to run on is a versioned native image - get the docker ref from the
                        # docker_native_image_config.json
                        native_image_ref = self._get_versioned_native_image(
                            native_image
                        )

                    if native_image_ref:
                        imgs.append(native_image_ref)
                        logger.info(
                            f"{log_prompt} - Native image to run on is: {native_image_ref}"
                        )

        elif docker_image_flag == DockerImageFlagOption.ALL_IMAGES.value:
            # Desirable docker images are the docker images from the yml file, the supported versioned native images
            # and the dev native image
            if imgs := self._get_all_docker_images(
                script_obj, script_id, supported_native_images
            ):
                logger.info(
                    f"{log_prompt} - Docker images to run on are: {', '.join(imgs)}"
                )

        else:
            # The flag is a specific docker image (from Docker Hub) or an invalid input -
            # In both cases we will try to run on the given input, if it does not exist in docker hub the run of lint
            # will fail later on.
            imgs.append(docker_image_flag)
            logger.info(
                f"{log_prompt} - Docker image to run on is: {docker_image_flag}"
            )

        return imgs

# STD python packages
import copy
import hashlib
import io
import json
import logging
import os
import platform
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

# 3-rd party packages
import docker
import docker.errors
import docker.models.containers
import requests.exceptions
import urllib3.exceptions
from demisto_sdk.commands.common.constants import (INTEGRATIONS_DIR,
                                                   PACKS_PACK_META_FILE_NAME,
                                                   TYPE_PWSH, TYPE_PYTHON)
# Local packages
from demisto_sdk.commands.common.tools import (get_all_docker_images,
                                               run_command_os)
from demisto_sdk.commands.lint.commands_builder import (
    build_bandit_command, build_flake8_command, build_mypy_command,
    build_pwsh_analyze_command, build_pwsh_test_command, build_pylint_command,
    build_pytest_command, build_vulture_command, build_xsoar_linter_command)
from demisto_sdk.commands.lint.helpers import (EXIT_CODES, FAIL, RERUN, RL,
                                               SUCCESS, WARNING,
                                               add_tmp_lint_files,
                                               add_typing_module,
                                               coverage_report_editor,
                                               get_checks_on_docker,
                                               get_checks_on_local_os,
                                               get_file_from_container,
                                               get_python_version_from_image,
                                               pylint_plugin,
                                               split_warnings_errors,
                                               stream_docker_container_output)
from jinja2 import Environment, FileSystemLoader, exceptions
from ruamel.yaml import YAML
from wcmatch.pathlib import NEGATE, Path

logger = logging.getLogger('demisto-sdk')


class Linter:
    """ Linter used to activate lint command on single package

        Attributes:
            pack_dir(Path): Pack to run lint on.
            content_repo(Path): Git repo object of content repo.
            req_2(list): requirements for docker using python2.
            req_3(list): requirements for docker using python3.
            docker_engine(bool):  Whether docker engine detected by docker-sdk.
    """

    def __init__(self, pack_dir: Path, content_repo: Path, req_3: list, req_2: list, docker_engine: bool):
        self._req_3 = req_3
        self._req_2 = req_2
        self._content_repo = content_repo
        self._pack_abs_dir = pack_dir
        self._pack_name = None
        # Docker client init
        if docker_engine:
            self._docker_client: docker.DockerClient = docker.from_env()
            self._docker_hub_login = self._docker_login()
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
            "commands": None
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
            "vulture_errors": None,
            "flake8_warnings": None,
            "XSOAR_linter_warnings": None,
            "bandit_warnings": None,
            "vulture_warnings": None,
            "exit_code": SUCCESS,
            "warning_code": SUCCESS,
        }

    def run_dev_packages(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool, no_vulture: bool,
                         no_xsoar_linter: bool, no_pwsh_analyze: bool, no_pwsh_test: bool, no_test: bool, modules: dict,
                         keep_container: bool, test_xml: str, no_coverage: bool) -> dict:
        """ Run lint and tests on single package
        Performing the follow:
            1. Run the lint on OS - flake8, bandit.
            2. Run in package docker - mypy, pylint, pytest.

        Args:
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
        skip = self._gather_facts(modules)
        # If not python pack - skip pack
        if skip:
            return self._pkg_lint_status
        try:
            # Locate mandatory files in pack path - for more info checkout the context manager LintFiles
            with add_tmp_lint_files(content_repo=self._content_repo,  # type: ignore
                                    pack_path=self._pack_abs_dir,
                                    lint_files=self._facts["lint_files"],
                                    modules=modules,
                                    pack_type=self._pkg_lint_status["pack_type"]):
                # Run lint check on host - flake8, bandit
                # in python2 files mypy will run in local os and in python3 mypy will run in docker container
                py_version = self._facts["python_version"]
                if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                    self._run_lint_in_host(no_flake8=no_flake8,
                                           no_bandit=no_bandit,
                                           no_mypy=no_mypy or 3 <= py_version,
                                           no_vulture=no_vulture,
                                           no_xsoar_linter=no_xsoar_linter)

                # Run lint and test check on pack docker image
                if self._facts["docker_engine"]:
                    self._run_lint_on_docker_image(no_mypy=no_mypy or py_version < 3,
                                                   no_pylint=no_pylint,
                                                   no_test=no_test,
                                                   no_pwsh_analyze=no_pwsh_analyze,
                                                   no_pwsh_test=no_pwsh_test,
                                                   keep_container=keep_container,
                                                   test_xml=test_xml,
                                                   no_coverage=no_coverage)
        except Exception as ex:
            err = f'{self._pack_abs_dir}: Unexpected fatal exception: {str(ex)}'
            logger.error(f"{err}. Traceback: {traceback.format_exc()}")
            self._pkg_lint_status["errors"].append(err)
            self._pkg_lint_status['exit_code'] += FAIL
        return self._pkg_lint_status

    def _gather_facts(self, modules: dict) -> bool:
        """ Gathering facts about the package - python version, docker images, valid docker image, yml parsing
        Args:
            modules(dict): Test mandatory modules to be ignore in lint check

        Returns:
            bool: Indicating if to continue further or not, if False exit Thread, Else continue.
        """
        # Looking for pkg yaml
        yml_file: Optional[Path] = self._pack_abs_dir.glob([r'*.yaml', r'*.yml', r'!*unified*.yml'], flags=NEGATE)

        if not yml_file:
            logger.info(f"{self._pack_abs_dir} - Skipping no yaml file found {yml_file}")
            self._pkg_lint_status["errors"].append('Unable to find yml file in package')
            return True
        else:
            try:
                yml_file = next(yml_file)
            except StopIteration:
                return True
        # Get pack name
        self._pack_name = yml_file.stem
        log_prompt = f"{self._pack_name} - Facts"
        self._pkg_lint_status["pkg"] = yml_file.stem
        logger.info(f"{log_prompt} - Using yaml file {yml_file}")
        # Parsing pack yaml - in order to verify if check needed
        try:

            script_obj: Dict = {}
            yml_obj: Dict = YAML().load(yml_file)
            if isinstance(yml_obj, dict):
                script_obj = yml_obj.get('script', {}) if isinstance(yml_obj.get('script'), dict) else yml_obj
            self._facts['is_script'] = True if 'Scripts' in yml_file.parts else False
            self._facts['is_long_running'] = script_obj.get('longRunning')
            self._facts['commands'] = self._get_commands_list(script_obj)
            self._pkg_lint_status["pack_type"] = script_obj.get('type')
        except (FileNotFoundError, IOError, KeyError):
            self._pkg_lint_status["errors"].append('Unable to parse package yml')
            return True
        # return no check needed if not python pack
        if self._pkg_lint_status["pack_type"] not in (TYPE_PYTHON, TYPE_PWSH):
            logger.info(f"{log_prompt} - Skipping due to not Python, Powershell package - Pack is"
                        f" {self._pkg_lint_status['pack_type']}")
            return True
        # Docker images
        if self._facts["docker_engine"]:
            logger.info(f"{log_prompt} - Pulling docker images, can take up to 1-2 minutes if not exists locally ")
            self._facts["images"] = [[image, -1] for image in get_all_docker_images(script_obj=script_obj)]
            # Gather environment variables for docker execution
            self._facts["env_vars"] = {
                "CI": os.getenv("CI", False),
                "DEMISTO_LINT_UPDATE_CERTS": os.getenv('DEMISTO_LINT_UPDATE_CERTS', "yes"),
                "PIP_QUIET": 3
            }
        lint_files = set()
        # Facts for python pack
        if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
            self._update_support_level()
            if self._facts["docker_engine"]:
                # Getting python version from docker image - verifying if not valid docker image configured
                for image in self._facts["images"]:
                    py_num: float = get_python_version_from_image(image=image[0])
                    image[1] = py_num
                    logger.info(f"{self._pack_name} - Facts - {image[0]} - Python {py_num}")
                    if not self._facts["python_version"]:
                        self._facts["python_version"] = py_num
                # Checking whatever *test* exists in package
                self._facts["test"] = True if next(self._pack_abs_dir.glob([r'test_*.py', r'*_test.py']),
                                                   None) else False
                if self._facts["test"]:
                    logger.info(f"{log_prompt} - Tests found")
                else:
                    logger.info(f"{log_prompt} - Tests not found")
                # Gather package requirements embedded test-requirements.py file
                test_requirements = self._pack_abs_dir / 'test-requirements.txt'
                if test_requirements.exists():
                    try:
                        additional_req = test_requirements.read_text(encoding='utf-8').strip().split('\n')
                        self._facts["additional_requirements"].extend(additional_req)
                        logger.info(f"{log_prompt} - Additional package Pypi packages found - {additional_req}")
                    except (FileNotFoundError, IOError):
                        self._pkg_lint_status["errors"].append('Unable to parse test-requirements.txt in package')
            elif not self._facts["python_version"]:
                # get python version from yml
                pynum = 3.7 if (script_obj.get('subtype', 'python3') == 'python3') else 2.7
                self._facts["python_version"] = pynum
                logger.info(f"{log_prompt} - Using python version from yml: {pynum}")
            # Get lint files
            lint_files = set(self._pack_abs_dir.glob(["*.py", "!__init__.py", "!*.tmp"],
                                                     flags=NEGATE))
        # Facts for Powershell pack
        elif self._pkg_lint_status["pack_type"] == TYPE_PWSH:
            # Get lint files
            lint_files = set(
                self._pack_abs_dir.glob(["*.ps1", "!*Tests.ps1", "CommonServerPowerShell.ps1", "demistomock.ps1'"],
                                        flags=NEGATE))

        # Add CommonServer to the lint checks
        if 'commonserver' in self._pack_abs_dir.name.lower():
            # Powershell
            if self._pkg_lint_status["pack_type"] == TYPE_PWSH:
                self._facts["lint_files"] = [Path(self._pack_abs_dir / 'CommonServerPowerShell.ps1')]
            # Python
            elif self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                self._facts["lint_files"] = [Path(self._pack_abs_dir / 'CommonServerPython.py')]
        else:
            test_modules = {self._pack_abs_dir / module.name for module in modules.keys()}
            lint_files = lint_files.difference(test_modules)
            self._facts["lint_files"] = list(lint_files)
        if self._facts["lint_files"]:
            for lint_file in self._facts["lint_files"]:
                logger.info(f"{log_prompt} - Lint file {lint_file}")
        else:
            logger.info(f"{log_prompt} - Lint files not found")

        self._split_lint_files()
        return False

    def _split_lint_files(self):
        """ Remove unit test files from _facts['lint_files'] and put into their own list _facts['lint_unittest_files']
        This is because not all lints should be done on unittest files.
        """
        lint_files_list = copy.deepcopy(self._facts["lint_files"])
        for lint_file in lint_files_list:
            if lint_file.name.startswith('test_') or lint_file.name.endswith('_test.py'):
                self._facts['lint_unittest_files'].append(lint_file)
                self._facts["lint_files"].remove(lint_file)

    def _run_lint_in_host(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_vulture: bool,
                          no_xsoar_linter: bool):
        """ Run lint check on host

        Args:
            no_flake8(bool): Whether to skip flake8.
            no_bandit(bool): Whether to skip bandit.
            no_vulture(bool): Whether to skip Vulture.
        """
        warning = []
        error = []
        other = []
        exit_code: int = 0
        for lint_check in get_checks_on_local_os(self._facts["python_version"]):
            exit_code = SUCCESS
            output = ""
            if self._facts["lint_files"] or self._facts["lint_unittest_files"]:
                if lint_check == "flake8" and not no_flake8:
                    flake8_lint_files = copy.deepcopy(self._facts["lint_files"])
                    # if there are unittest.py then we would run flake8 on them too.
                    if self._facts['lint_unittest_files']:
                        flake8_lint_files.extend(self._facts['lint_unittest_files'])
                    exit_code, output = self._run_flake8(py_num=self._facts["python_version"],
                                                         lint_files=flake8_lint_files)

            if self._facts["lint_files"]:
                if lint_check == "XSOAR_linter" and not no_xsoar_linter:
                    exit_code, output = self._run_xsoar_linter(py_num=self._facts["python_version"],
                                                               lint_files=self._facts["lint_files"])
                elif lint_check == "mypy" and not no_mypy:
                    exit_code, output = self._run_mypy(py_num=self._facts["python_version"],
                                                       lint_files=self._facts["lint_files"])

                elif lint_check == "bandit" and not no_bandit:
                    exit_code, output = self._run_bandit(lint_files=self._facts["lint_files"])

                elif lint_check == "vulture" and not no_vulture:
                    exit_code, output = self._run_vulture(py_num=self._facts["python_version"],
                                                          lint_files=self._facts["lint_files"])

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

    def _run_flake8(self, py_num: float, lint_files: List[Path]) -> Tuple[int, str]:
        """ Runs flake8 in pack dir

        Args:
            py_num(float): The python version in use
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Flake8"
        logger.info(f"{log_prompt} - Start")
        stdout, stderr, exit_code = run_command_os(command=build_flake8_command(lint_files, py_num),
                                                   cwd=self._content_repo)
        logger.debug(f"{log_prompt} - Finished exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finished errors found")
            if stderr:
                return FAIL, stderr
            else:
                return FAIL, stdout

        logger.info(f"{log_prompt} - Successfully finished")

        return SUCCESS, ""

    def _run_xsoar_linter(self, py_num: float, lint_files: List[Path]) -> Tuple[int, str]:
        """ Runs Xsaor linter in pack dir

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
            if myenv.get('PYTHONPATH'):
                myenv['PYTHONPATH'] += ':' + str(self._pack_abs_dir)
            else:
                myenv['PYTHONPATH'] = str(self._pack_abs_dir)
            if self._facts['is_long_running']:
                myenv['LONGRUNNING'] = 'True'
            if py_num < 3:
                myenv['PY2'] = 'True'
            myenv['is_script'] = str(self._facts['is_script'])
            # as Xsoar checker is a pylint plugin and runs as part of pylint code, we can not pass args to it.
            # as a result we can use the env vars as a getway.
            myenv['commands'] = ','.join([str(elem) for elem in self._facts['commands']]) \
                if self._facts['commands'] else ''
            stdout, stderr, exit_code = run_command_os(
                command=build_xsoar_linter_command(lint_files, py_num, self._facts.get('support_level', 'base')),
                cwd=self._pack_abs_dir, env=myenv)
        if exit_code & FAIL_PYLINT:
            logger.info(f"{log_prompt}- Finished errors found")
            status = FAIL
        if exit_code & WARNING:
            logger.info(f"{log_prompt} - Finished warnings found")
            if not status:
                status = WARNING
        # if pylint did not run and failure exit code has been returned from run commnad
        elif exit_code & FAIL:
            status = FAIL
            # for contrib prs which are not merged from master and do not have pylint in dev-requirements-py2.
            if os.environ.get('CI'):
                stdout = "Xsoar linter could not run, Please merge from master"
            else:
                stdout = "Xsoar linter could not run, please make sure you have" \
                         " the necessary Pylint version for both py2 and py3"
            logger.info(f"{log_prompt}- Finished errors found")

        logger.debug(f"{log_prompt} - Finished exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished stderr: {RL if stderr else ''}{stderr}")

        if not exit_code:
            logger.info(f"{log_prompt} - Successfully finished")

        return status, stdout

    def _run_bandit(self, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run bandit in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Bandit"
        logger.info(f"{log_prompt} - Start")
        stdout, stderr, exit_code = run_command_os(command=build_bandit_command(lint_files),
                                                   cwd=self._pack_abs_dir)
        logger.debug(f"{log_prompt} - Finished exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finished Finished errors found")
            if stderr:
                return FAIL, stderr
            else:
                return FAIL, stdout

        logger.info(f"{log_prompt} - Successfully finished")

        return SUCCESS, ""

    def _run_mypy(self, py_num: float, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run mypy in pack dir

        Args:
            py_num(float): The python version in use
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Mypy"
        logger.info(f"{log_prompt} - Start")
        with add_typing_module(lint_files=lint_files, python_version=py_num):
            stdout, stderr, exit_code = run_command_os(command=build_mypy_command(files=lint_files, version=py_num),
                                                       cwd=self._pack_abs_dir)
        logger.debug(f"{log_prompt} - Finished exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finished Finished errors found")
            if stderr:
                return FAIL, stderr
            else:
                return FAIL, stdout

        logger.info(f"{log_prompt} - Successfully finished")

        return SUCCESS, ""

    def _run_vulture(self, py_num: float, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run vulture in pack dir

        Args:
            py_num(float): The python version in use
            lint_files(List[Path]): file to perform lint

        Returns:
           int: 0 on successful else 1, errors
           str: Vulture errors
        """
        log_prompt = f"{self._pack_name} - Vulture"
        logger.info(f"{log_prompt} - Start")
        stdout, stderr, exit_code = run_command_os(command=build_vulture_command(files=lint_files,
                                                                                 pack_path=self._pack_abs_dir,
                                                                                 py_num=py_num),
                                                   cwd=self._pack_abs_dir)
        logger.debug(f"{log_prompt} - Finished exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finished stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finished stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finished Finished errors found")
            if stderr:
                return FAIL, stderr
            else:
                return FAIL, stdout

        logger.info(f"{log_prompt} - Successfully finished")

        return SUCCESS, ""

    def _run_lint_on_docker_image(self, no_mypy: bool, no_pylint: bool, no_test: bool, no_pwsh_analyze: bool, no_pwsh_test: bool,
                                  keep_container: bool, test_xml: str, no_coverage: bool):
        """ Run lint check on docker image

        Args:
            no_mypy(bool): Whether to skip mypy
            no_pylint(bool): Whether to skip pylint
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
            no_coverage(bool): Run pytest without coverage report

        """
        for image in self._facts["images"]:
            # Docker image status - visualize
            status = {
                "image": image[0],
                "image_errors": "",
                "pylint_errors": "",
                "pytest_errors": "",
                "pytest_json": {},
                "pwsh_analyze_errors": "",
                "pwsh_test_errors": ""
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
                for check in get_checks_on_docker(self._facts["python_version"]):  # ["mypy", "pylint", "pytest", "pwsh_analyze", "pwsh_test"]:
                    exit_code = SUCCESS
                    output = ""
                    for trial in range(2):
                        if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                            # Perform mypy
                            if not no_mypy and check == "mypy" and self._facts["lint_files"]:
                                test_command = build_mypy_command(files=self._facts["lint_files"],
                                                                  version=self._facts["python_version"])
                                exit_code, output = self._run_tests_in_docker(test_name=check.capitalize(),
                                                                              test_command=test_command,
                                                                              test_image=image_id,
                                                                              keep_container=keep_container)

                            # Perform pylint
                            if not no_pylint and check == "pylint" and self._facts["lint_files"]:
                                test_command = build_pylint_command(files=self._facts["lint_files"],
                                                                    docker_version=self._facts["python_version"])
                                exit_code, output = self._run_tests_in_docker(test_name=check.capitalize(),
                                                                              test_command=test_command,
                                                                              test_image=image_id,
                                                                              keep_container=keep_container)
                            # Perform pytest
                            elif not no_test and self._facts["test"] and check == "pytest":
                                exit_code, output, test_json = self._docker_run_pytest(test_image=image_id,
                                                                                       keep_container=keep_container,
                                                                                       test_xml=test_xml,
                                                                                       no_coverage=no_coverage)
                                status["pytest_json"] = test_json
                        elif self._pkg_lint_status["pack_type"] == TYPE_PWSH:
                            # Perform powershell analyze
                            if not no_pwsh_analyze and check == "pwsh_analyze" and self._facts["lint_files"]:
                                exit_code, output = self._docker_run_pwsh_analyze(test_image=image_id,
                                                                                  keep_container=keep_container)
                            # Perform powershell test
                            elif not no_pwsh_test and check == "pwsh_test":
                                exit_code, output = self._docker_run_pwsh_test(test_image=image_id,
                                                                               keep_container=keep_container)
                        # If lint check perfrom and failed on reason related to enviorment will run twice,
                        # But it failing in second time it will count as test failure.
                        if (exit_code == RERUN and trial == 1) or exit_code == FAIL or exit_code == SUCCESS:
                            if exit_code in [RERUN, FAIL]:
                                self._pkg_lint_status["exit_code"] |= EXIT_CODES[check]
                                status[f"{check}_errors"] = output
                            break
            else:
                status["image_errors"] = str(errors)
                self._pkg_lint_status["exit_code"] += EXIT_CODES["image"]

            # Add image status to images
            self._pkg_lint_status["images"].append(status)
            try:
                self._docker_client.images.remove(image_id)
            except (docker.errors.ImageNotFound, docker.errors.APIError):
                pass

    def _docker_login(self) -> bool:
        """ Login to docker-hub using environment variables:
                1. DOCKERHUB_USER - User for docker hub.
                2. DOCKERHUB_PASSWORD - Password for docker-hub.
            Used in Circle-CI for pushing into repo devtestdemisto

        Returns:
            bool: True if logged in successfully.
        """
        docker_user = os.getenv('DOCKERHUB_USER')
        docker_pass = os.getenv('DOCKERHUB_PASSWORD')
        try:
            self._docker_client.login(username=docker_user,
                                      password=docker_pass,
                                      registry="https://index.docker.io/v1")
            return self._docker_client.ping()
        except docker.errors.APIError:
            return False

    def _docker_image_create(self, docker_base_image: List[Any]) -> Tuple[str, str]:
        """ Create docker image:
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
        test_image_id = ""
        # Get requirements file for image
        requirements = []
        if 2 < docker_base_image[1] < 3:
            requirements = self._req_2
        elif docker_base_image[1] > 3:
            requirements = self._req_3
        # Using DockerFile template
        file_loader = FileSystemLoader(Path(__file__).parent / 'templates')
        env = Environment(loader=file_loader, lstrip_blocks=True, trim_blocks=True, autoescape=True)
        template = env.get_template('dockerfile.jinja2')
        try:
            dockerfile = template.render(image=docker_base_image[0],
                                         pypi_packs=requirements + self._facts["additional_requirements"],
                                         pack_type=self._pkg_lint_status["pack_type"],
                                         copy_pack=False)
        except exceptions.TemplateError as e:
            logger.debug(f"{log_prompt} - Error when build image - {e.message()}")
            return test_image_id, str(e)
        # Trying to pull image based on dockerfile hash, will check if something changed
        errors = ""
        test_image_name = f'devtest{docker_base_image[0]}-{hashlib.md5(dockerfile.encode("utf-8")).hexdigest()}'
        test_image = None
        try:
            logger.info(f"{log_prompt} - Trying to pull existing image {test_image_name}")
            test_image = self._docker_client.images.pull(test_image_name)
        except (docker.errors.APIError, docker.errors.ImageNotFound):
            logger.info(f"{log_prompt} - Unable to find image {test_image_name}")
        # Creatng new image if existing image isn't found
        if not test_image:
            logger.info(
                f"{log_prompt} - Creating image based on {docker_base_image[0]} - Could take 2-3 minutes at first "
                f"time")
            try:
                with io.BytesIO() as f:
                    f.write(dockerfile.encode('utf-8'))
                    f.seek(0)
                    self._docker_client.images.build(fileobj=f,
                                                     tag=test_image_name,
                                                     forcerm=True)

                    if self._docker_hub_login:
                        for trial in range(2):
                            try:
                                self._docker_client.images.push(test_image_name)
                                logger.info(f"{log_prompt} - Image {test_image_name} pushed to repository")
                                break
                            except (requests.exceptions.ConnectionError, urllib3.exceptions.ReadTimeoutError):
                                logger.info(f"{log_prompt} - Unable to push image {test_image_name} to repository")

            except (docker.errors.BuildError, docker.errors.APIError, Exception) as e:
                logger.critical(f"{log_prompt} - Build errors occurred {e}")
                errors = str(e)
        else:
            logger.info(f"{log_prompt} - Found existing image {test_image_name}")
        dockerfile_path = Path(self._pack_abs_dir / ".Dockerfile")
        dockerfile = template.render(image=test_image_name,
                                     copy_pack=True)
        with open(dockerfile_path, mode="w+") as file:
            file.write(str(dockerfile))
        # we only do retries in CI env where docker build is sometimes flacky
        build_tries = int(os.getenv('DEMISTO_SDK_DOCKER_BUILD_TRIES', 3)) if os.getenv('CI') else 1
        for trial in range(build_tries):
            try:
                logger.info(f"{log_prompt} - Copy pack dir to image {test_image_name}")
                docker_image_final = self._docker_client.images.build(path=str(dockerfile_path.parent),
                                                                      dockerfile=dockerfile_path.stem,
                                                                      forcerm=True)
                test_image_name = docker_image_final[0].short_id
                break
            except Exception as e:
                logger.exception(f"{log_prompt} - errors occurred when building image in dir {e}")
                if trial >= build_tries:
                    errors = str(e)
                else:
                    logger.info(f"{log_prompt} - sleeping 2 seconds and will retry build after")
                    time.sleep(2)
        if dockerfile_path.exists():
            dockerfile_path.unlink()

        if test_image_id:
            logger.info(f"{log_prompt} - Image {test_image_id} created successfully")

        return test_image_name, errors

    def _docker_remove_container(self, container_name: str):
        try:
            container_obj = self._docker_client.containers.get(container_name)
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass
        except requests.exceptions.ChunkedEncodingError as err:
            # see: https://github.com/docker/docker-py/issues/2696#issuecomment-721322548
            if platform.system() != 'Darwin' or 'Connection broken' not in str(err):
                raise

    def _run_tests_in_docker(self, test_name: str, test_command: str, test_image: str, keep_container: bool) -> Tuple[int, str]:
        """ Run tests (Mypy, Pylint etc.) in created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after execution finished

        Returns:
            int: 0 on successful, errors 1, need to retry 2
            str: Container log
        """
        log_prompt = f'{self._pack_name} - {test_name} - Image {test_image}'
        logger.info(f"{log_prompt} - Start")
        container_name = f"{self._pack_name}-{test_name.lower()}"
        # Check if previous run left container a live if it do, we remove it
        self._docker_remove_container(container_name)

        # Run container
        exit_code = SUCCESS
        output = ""
        try:
            container_obj: docker.models.containers.Container = self._docker_client.containers.run(
                name=container_name,
                image=test_image,
                command=[test_command],
                user=f"{os.getuid()}:4000",
                detach=True,
                environment=self._facts["env_vars"]
            )
            stream_docker_container_output(container_obj.logs(stream=True))
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code in [1, 2]:
                # 1-fatal message issued
                # 2-Error message issued
                exit_code = FAIL
                output = container_log
                logger.info(f"{log_prompt} - Finished errors found")
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
            # Keeping container if needed or remove it
            if keep_container:
                print(f"{log_prompt} - container name {container_name}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        except Exception as e:
            logger.exception(f"{log_prompt} - Unable to run {test_name.lower()}")
            exit_code = RERUN
            output = str(e)
        return exit_code, output

    def _docker_run_pytest(self, test_image: str, keep_container: bool, test_xml: str, no_coverage: bool = False) -> Tuple[int, str, dict]:
        """ Run Pytest in created test image

        Args:
            test_image(str): Test image id/name
            keep_container(bool): True if to keep container after execution finished
            test_xml(str): Xml saving path
            no_coverage(bool): Run pytest without coverage report
        Returns:
            int: 0 on successful, errors 1, need to retry 2
            str: Unit test json report
        """
        log_prompt = f'{self._pack_name} - Pytest - Image {test_image}'
        logger.info(f"{log_prompt} - Start")
        container_name = f"{self._pack_name}-pytest"
        # Check if previous run left container a live if it does, Remove it
        self._docker_remove_container(container_name)
        # Collect tests
        exit_code = SUCCESS
        output = ''
        test_json = {}
        try:
            # Running pytest container
            cov = '' if no_coverage else self._pack_abs_dir.stem
            container_obj: docker.models.containers.Container = self._docker_client.containers.run(
                name=container_name, image=test_image, command=[build_pytest_command(test_xml=test_xml, json=True,
                                                                                     cov=cov)],
                user=f"{os.getuid()}:4000", detach=True, environment=self._facts["env_vars"])
            stream_docker_container_output(container_obj.logs(stream=True))
            # Waiting for container to be finished
            container_status: dict = container_obj.wait(condition="exited")
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
                    test_data_xml = get_file_from_container(container_obj=container_obj,
                                                            container_path="/devwork/report_pytest.xml")
                    xml_apth = Path(test_xml) / f'{self._pack_name}_pytest.xml'
                    with open(file=xml_apth, mode='bw') as f:
                        f.write(test_data_xml)  # type: ignore

                if not no_coverage:
                    cov_file_path = os.path.join(self._pack_abs_dir, '.coverage')
                    cov_data = get_file_from_container(container_obj=container_obj,
                                                       container_path="/devwork/.coverage")
                    cov_data = cov_data if isinstance(cov_data, bytes) else cov_data.encode()
                    with open(cov_file_path, 'wb') as coverage_file:
                        coverage_file.write(cov_data)
                    coverage_report_editor(cov_file_path, os.path.join(self._pack_abs_dir, f'{self._pack_abs_dir.stem}.py'))

                test_json = json.loads(get_file_from_container(container_obj=container_obj,
                                                               container_path="/devwork/report_pytest.json",
                                                               encoding="utf-8"))
                for test in test_json.get('report', {}).get("tests"):
                    if test.get("call", {}).get("longrepr"):
                        test["call"]["longrepr"] = test["call"]["longrepr"].split('\n')
                if container_exit_code in [0, 5]:
                    logger.info(f"{log_prompt} - Successfully finished")
                    exit_code = SUCCESS
                elif container_exit_code in [2]:
                    output = container_obj.logs().decode('utf-8')
                    exit_code = FAIL
                else:
                    logger.info(f"{log_prompt} - Finished errors found")
                    exit_code = FAIL
            elif container_exit_code in [3, 4]:
                # 3-Internal error happened while executing tests
                # 4-pytest command line usage error
                logger.critical(f"{log_prompt} - Usage error")
                exit_code = RERUN
                output = container_obj.logs().decode('utf-8')
            # Remove container if not needed
            if keep_container:
                print(f"{log_prompt} - Container name {container_name}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to remove container {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{log_prompt} - Unable to run pytest container {e}")
            exit_code = RERUN

        return exit_code, output, test_json

    def _docker_run_pwsh_analyze(self, test_image: str, keep_container: bool) -> Tuple[int, str]:
        """ Run Powershell code analyze in created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after excution finished

        Returns:
            int: 0 on successful, errors 1, need to retry 2
            str: Container log
        """
        log_prompt = f'{self._pack_name} - Powershell analyze - Image {test_image}'
        logger.info(f"{log_prompt} - Start")
        container_name = f"{self._pack_name}-pwsh-analyze"
        # Check if previous run left container a live if it do, we remove it
        container_obj: docker.models.containers.Container
        try:
            container_obj = self._docker_client.containers.get(container_name)
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Run container
        exit_code = SUCCESS
        output = ""
        try:
            container_obj = self._docker_client.containers.run(name=container_name,
                                                               image=test_image,
                                                               command=build_pwsh_analyze_command(
                                                                   self._facts["lint_files"][0]),
                                                               user=f"{os.getuid()}:4000",
                                                               detach=True,
                                                               environment=self._facts["env_vars"])
            stream_docker_container_output(container_obj.logs(stream=True))
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code:
                # 1-fatal message issued
                # 2-Error message issued
                logger.info(f"{log_prompt} - Finished errors found")
                output = container_log
                exit_code = FAIL
            else:
                logger.info(f"{log_prompt} - Successfully finished")
            # Keeping container if needed or remove it
            if keep_container:
                print(f"{log_prompt} - container name {container_name}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{log_prompt} - Unable to run powershell test - {e}")
            exit_code = RERUN

        return exit_code, output

    def _update_support_level(self):
        pack_dir = self._pack_abs_dir.parent if self._pack_abs_dir.parts[-1] == INTEGRATIONS_DIR else \
            self._pack_abs_dir.parent.parent
        pack_meta_content: Dict = json.load((pack_dir / PACKS_PACK_META_FILE_NAME).open())
        self._facts['support_level'] = pack_meta_content.get('support')
        if self._facts['support_level'] == 'partner' and pack_meta_content.get('Certification'):
            self._facts['support_level'] = 'certified partner'

    def _docker_run_pwsh_test(self, test_image: str, keep_container: bool) -> Tuple[int, str]:
        """ Run Powershell tests in created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after excution finished

        Returns:
            int: 0 on successful, errors 1, neet to retry 2
            str: Container log
        """
        log_prompt = f'{self._pack_name} - Powershell test - Image {test_image}'
        logger.info(f"{log_prompt} - Start")
        container_name = f"{self._pack_name}-pwsh-test"
        # Check if previous run left container a live if it do, we remove it
        self._docker_remove_container(container_name)

        # Run container
        exit_code = SUCCESS
        output = ""
        try:
            container_obj: docker.models.containers.Container = self._docker_client.containers.run(
                name=container_name, image=test_image, command=build_pwsh_test_command(),
                user=f"{os.getuid()}:4000", detach=True, environment=self._facts["env_vars"])
            stream_docker_container_output(container_obj.logs(stream=True))
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.info(f"{log_prompt} - exit-code: {container_exit_code}")
            if container_exit_code:
                # 1-fatal message issued
                # 2-Error message issued
                logger.info(f"{log_prompt} - Finished errors found")
                output = container_log
                exit_code = FAIL
            else:
                logger.info(f"{log_prompt} - Successfully finished")
            # Keeping container if needed or remove it
            if keep_container:
                print(f"{log_prompt} - container name {container_name}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{log_prompt} - Unable to run powershell test - {e}")
            exit_code = RERUN

        return exit_code, output

    def _get_commands_list(self, script_obj: dict):
        """ Get all commands from yml file of the pack
           Args:
               script_obj(dict): the script section of the yml file.
           Returns:
               list: list of all commands
        """
        commands_list = []
        try:
            commands_obj = script_obj.get('commands', {})
            for command in commands_obj:
                commands_list.append(command.get('name', ''))
        except Exception:
            logger.debug("Failed getting the commands from the yml file")
        return commands_list

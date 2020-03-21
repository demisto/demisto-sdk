# STD python packages
import logging
from typing import Tuple, List, Optional
import tempfile
import os
import json
import hashlib
import urllib3.exceptions
import requests.exceptions
# 3-rd party packages
import docker.errors
import docker.models.containers
import docker
from jinja2 import Environment, FileSystemLoader, exceptions
from ruamel.yaml import YAML
from wcmatch.pathlib import Path, BRACE, NEGATE
# Local packages
from demisto_sdk.commands.common.tools import get_all_docker_images
from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.lint.commands_builder import build_mypy_command, build_bandit_command, build_pytest_command, \
    build_pylint_command, build_flake8_command, build_vulture_command, build_pwsh_analyze_command, build_pwsh_test_command
from demisto_sdk.commands.lint.helpers import get_file_from_container, get_python_version_from_image, \
    run_command_os, add_tmp_lint_files, copy_dir_to_container, EXIT_CODES, add_typing_module, RL

logger = logging.getLogger('demisto-sdk')


class Linter:
    """ Linter used to activate lint command on single package

        Attributes:
            pack_dir(Path): Pack to run lint on.
            req_2(list): requirements for docker using python2.
            req_3(list): requirements for docker using python3.
            docker_engine(bool):  Wheter docker engine detected by docker-sdk.
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
        self._facts = {
            "images": [],
            "python_version": 0,
            "env_vars": {},
            "test": False,
            "lint_files": [],
            "additional_requirements": [],
            "docker_engine": docker_engine
        }
        # Pack lint status object - visualize it
        self._pkg_lint_status = {
            "pkg": None,
            "pack_type": None,
            "path": str(self._pack_abs_dir),
            "errors": [],
            "images": [],
            "flake8_errors": None,
            "bandit_errors": None,
            "mypy_errors": None,
            "vulture_errors": None,
            "exit_code": 0
        }

    def run_dev_packages(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool, no_vulture: bool,
                         no_pwsh_analyze: bool, no_pwsh_test: bool, no_test: bool, modules: dict, keep_container: bool,
                         test_xml: str) -> dict:
        """ Run lint and tests on single package
        Perfroming the follow:
            1. Run the lint on OS - flake8, bandit, mypy.
            2. Run in package docker - pylint, pytest.

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

        Returns:
            dict: lint and test all status, pkg status)
        """
        # Gather information for lint check information
        skip = self._gather_facts(modules)
        # If not python pack - skip pack
        if skip:
            return 0b0, self._pkg_lint_status

        # Locate mandatory files in pack path - for more info checkout the context manager LintFiles
        with add_tmp_lint_files(content_repo=self._content_repo,
                                pack_path=self._pack_abs_dir,
                                lint_files=self._facts["lint_files"],
                                modules=modules,
                                pack_type=self._pkg_lint_status["pack_type"]):
            # Run lint check on host - flake8, bandit, mypy
            if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                self._run_lint_in_host(no_flake8=no_flake8,
                                       no_bandit=no_bandit,
                                       no_mypy=no_mypy,
                                       no_vulture=no_vulture)
            # Run lint and test check on pack docker image
            if self._facts["docker_engine"]:
                self._run_lint_on_docker_image(no_pylint=no_pylint,
                                               no_test=no_test,
                                               no_pwsh_analyze=no_pwsh_analyze,
                                               no_pwsh_test=no_pwsh_test,
                                               keep_container=keep_container,
                                               test_xml=test_xml)

        return self._pkg_lint_status

    def _gather_facts(self, modules: dict) -> bool:
        """ Gathering facts about the package - python version, docker images, vaild docker image, yml parsing
        Args:
            modules(dict): Test mandatory modules to be ignore in lint check

        Returns:
            bool: Indicating if to continue further or not, if False exit Thread, Else continue.
        """
        # Loooking for pkg yaml
        yml_file: Optional[Path] = next(self._pack_abs_dir.glob(rf'*.{{yml,yaml}}', flags=BRACE), None)
        if not yml_file:
            logger.info(f"{self._pack_abs_dir} - Skiping no yaml file found {yml_file}")
            self._pkg_lint_status["errors"].append('Unable to find yml file in package')
            return True
        # Get pack name
        self._pack_name = yml_file.stem
        log_prompt = f"{self._pack_name} - Facts"
        self._pkg_lint_status["pkg"] = yml_file.stem
        logger.info(f"{log_prompt} - Using yaml file {yml_file}")
        # Parsing pack yaml - inorder to verify if check needed
        try:
            script_obj: dict = {}
            yml_obj: dict = YAML().load(yml_file)
            if isinstance(yml_obj, dict):
                script_obj: dict = yml_obj.get('script') if isinstance(yml_obj.get('script'), dict) else yml_obj
            self._pkg_lint_status["pack_type"] = script_obj.get('type')
        except (FileNotFoundError, IOError, KeyError):
            self._pkg_lint_status["errors"].append('Unable to parse package yml')
            return True
        # return no check needed if not python pack
        if self._pkg_lint_status["pack_type"] not in (TYPE_PYTHON, TYPE_PWSH):
            logger.info(f"{log_prompt} - Skippring due to not Python, Powershell package - Pack is"
                        f" {self._pkg_lint_status['pack_type']}")
            return True
        # Docker images
        if self._facts["docker_engine"]:
            self._facts["images"] = [[image, -1] for image in get_all_docker_images(script_obj=script_obj)]
            # Gather enviorment variables for docker execution
            self._facts["env_vars"] = {
                "CI": os.getenv("CI", False),
                "DEMISTO_LINT_UPDATE_CERTS": os.getenv('DEMISTO_LINT_UPDATE_CERTS', "yes")
            }
        if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
            if self._facts["docker_engine"]:
                # Getting python version from docker image - verfying if not valid docker image configured
                for image in self._facts["images"]:
                    py_num: float = get_python_version_from_image(image=image[0])
                    image[1] = py_num
                    logger.info(f"{self._pack_name} - Facts - {image[0]} - Python {py_num}")
                    if not self._facts["python_version"]:
                        self._facts["python_version"] = py_num
                # Checking wheter *test* exsits in package
                self._facts["test"] = True if next(self._pack_abs_dir.glob([r'test_*.py', r'*_test.py']), None) else False
                if self._facts["test"]:
                    logger.info(f"{log_prompt} - Tests found")
                else:
                    logger.info(f"{log_prompt} - Tests not found")
                # Gather package requirements embeded test-requirements.py file
                test_requirements = self._pack_abs_dir / 'test-requirements.txt'
                if test_requirements.exists():
                    try:
                        additional_req = test_requirements.read_text(encoding='utf-8')
                        self._facts["additinal_requirements"].extend(additional_req)
                        logger.info(f"{log_prompt} - Additional package Pypi packages found - {additional_req}")
                    except (FileNotFoundError, IOError):
                        self._pkg_lint_status["errors"].append('Unable to parse test-requirements.txt in package')
            # Get lint files
            lint_files = set(self._pack_abs_dir.glob(["*.py", "!*_test.py", "!test_*.py", "!__init__.py", "!*.tmp"],
                                                     flags=NEGATE))
            test_modules = {self._pack_abs_dir / module.name for module in modules.keys()}
            lint_files = lint_files.difference(test_modules)
            self._facts["lint_files"] = list(lint_files)
            logger.info(f"{log_prompt} - Lint files {lint_files}")
        elif self._pkg_lint_status["pack_type"] == TYPE_PWSH:
            # Get lint files
            self._facts["lint_files"] = list(self._pack_abs_dir.glob(["*.ps1"], flags=NEGATE))
            for lint_file in self._facts["lint_files"]:
                logger.info(f"{log_prompt} - Lint files {lint_file}")

        return False

    def _run_lint_in_host(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_vulture: bool):
        """ Run lint check on host

        Args:
            no_flake8(bool): Whether to skip flake8.
            no_bandit(bool): Whether to skip bandit.
            no_mypy(bool): Whether to skip mypy.
            no_vulture(bool): Whether to skip Vulture.
        """
        if self._facts["lint_files"]:
            for lint_check in ["flake8", "bandit", "mypy", "vulture"]:
                exit_code: int = 0b0
                output: str = ""
                if lint_check == "flake8" and not no_flake8:
                    exit_code, output = self._run_flake8(lint_files=self._facts["lint_files"])
                elif lint_check == "bandit" and not no_bandit:
                    exit_code, output = self._run_bandit(lint_files=self._facts["lint_files"])
                elif lint_check == "mypy" and not no_mypy and self._facts["docker_engine"]:
                    exit_code, output = self._run_mypy(py_num=self._facts["images"][0][1],
                                                       lint_files=self._facts["lint_files"])
                elif lint_check == "vulture" and not no_vulture and self._facts["docker_engine"]:
                    exit_code, output = self._run_vulture(py_num=self._facts["python_version"],
                                                          lint_files=self._facts["lint_files"])
                if exit_code:
                    self._pkg_lint_status["exit_code"] += EXIT_CODES[lint_check]
                    self._pkg_lint_status[f"{lint_check}_errors"] = output

    def _run_flake8(self, lint_files: List[Path]) -> Tuple[int, str]:
        """ Runs flake8 in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Flake8"
        logger.info(f"{log_prompt} - Start")
        stdout, stderr, exit_code = run_command_os(command=build_flake8_command(lint_files),
                                                   cwd=self._pack_abs_dir)
        logger.debug(f"{log_prompt} - Finshed exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finshed stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finshed stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finshed Finshed errors found")
            if stderr:
                return 1, stderr
            else:
                return 1, stdout

        logger.info(f"{log_prompt} - Finshed success")

        return 0, ""

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
        logger.debug(f"{log_prompt} - Finshed exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finshed stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finshed stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finshed Finshed errors found")
            if stderr:
                return 1, stderr
            else:
                return 1, stdout

        logger.info(f"{log_prompt} - Finshed success")

        return 0, ""

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
        logger.debug(f"{log_prompt} - Finshed exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finshed stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finshed stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finshed Finshed errors found")
            if stderr:
                return 1, stderr
            else:
                return 1, stdout

        logger.info(f"{log_prompt} - Finshed success")

        return 0, ""

    def _run_vulture(self, py_num: float, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run mypy in pack dir

        Args:
            py_num(float): The python version in use
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        log_prompt = f"{self._pack_name} - Vulture"
        logger.info(f"{log_prompt} - Start")
        stdout, stderr, exit_code = run_command_os(command=build_vulture_command(files=lint_files,
                                                                                 pack_path=self._pack_abs_dir,
                                                                                 version=py_num),
                                                   cwd=self._pack_abs_dir)
        logger.debug(f"{log_prompt} - Finshed exit-code: {exit_code}")
        logger.debug(f"{log_prompt} - Finshed stdout: {RL if stdout else ''}{stdout}")
        logger.debug(f"{log_prompt} - Finshed stderr: {RL if stderr else ''}{stderr}")
        if stderr or exit_code:
            logger.info(f"{log_prompt}- Finshed Finshed errors found")
            if stderr:
                return 1, stderr
            else:
                return 1, stdout

        logger.info(f"{log_prompt} - Finshed success")

        return 0, ""

    def _run_lint_on_docker_image(self, no_pylint: list, no_test: bool, no_pwsh_analyze: bool, no_pwsh_test: bool,
                                  keep_container: bool, test_xml: str):
        """ Run lint check on docker image

        Args:
            no_pylint(bool): Whether to skip pylint
            no_test(bool): Whether to skip pytest
            no_pwsh_analyze(bool): Whether to skip powershell code analyzing
            no_pwsh_test(bool): whether to skip powershell tests
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results
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
            # Creating image if pylint specifie or found tests and tests specified
            image_id = ""
            errors = ""
            for trial in range(2):
                image_id, errors = self._docker_image_create(docker_base_image=image,
                                                             no_test=no_test)
                if not errors:
                    break

            if image_id and not errors:
                # Set image creation status
                for check in ["pylint", "pytest", "pwsh_analyze", "pwsh_test"]:
                    exit_code = 0b0
                    output = ""
                    for trial in range(2):
                        if self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
                            # Perform pylint
                            if not no_pylint and check == "pylint" and self._facts["lint_files"]:
                                exit_code, output = self._docker_run_pylint(test_image=image_id,
                                                                            keep_container=keep_container)
                            # Perform pytest
                            elif not no_test and self._facts["test"] and check == "pytest":
                                exit_code, test_json = self._docker_run_pytest(test_image=image_id,
                                                                               keep_container=keep_container,
                                                                               test_xml=test_xml)
                                status["pytest_json"]: dict = test_json
                        elif self._pkg_lint_status["pack_type"] == TYPE_PWSH:
                            # Perform powershell analyze
                            if not no_pwsh_analyze and check == "pwsh_analyze":
                                exit_code, output = self._docker_run_pwsh_analyze(test_image=image_id,
                                                                                  keep_container=keep_container)
                            # Perform powershell test
                            elif not no_pwsh_test and check == "pwsh_test":
                                exit_code, output = self._docker_run_pwsh_test(test_image=image_id,
                                                                               keep_container=keep_container)

                        if (exit_code != 0b10 or trial == 2) and exit_code:
                            self._pkg_lint_status["exit_code"] += EXIT_CODES[check]
                            status[f"{check}_errors"] = output
                            break
                        elif exit_code != 0b10:
                            break
            else:
                status["image_errors"] = str(errors)
                self._pkg_lint_status["exit_code"] += EXIT_CODES["image"]

            # Add image status to images
            self._pkg_lint_status["images"].append(status)

    def _docker_login(self) -> bool:
        docker_user = os.getenv('DOCKERHUB_USER')
        docker_pass = os.getenv('DOCKERHUB_PASSWORD')
        try:
            self._docker_client.login(username=docker_user,
                                      password=docker_pass,
                                      registry="https://index.docker.io/v1")
            return self._docker_client.ping()
        except docker.errors.APIError:
            return False

    def _docker_image_create(self, docker_base_image: str, no_test: bool) -> str:
        """ Create docker image:
            1. Installing 'build base' if required in alpine images version - https://wiki.alpinelinux.org/wiki/GCC
            2. Installing pypi packs - if only pylint required - only pylint installed otherwise all pytest and pylint
               installed, packages which being install can be found in path demisto_sdk/commands/lint/dev_envs
            3. The docker image build done by Dockerfile template located in
                demisto_sdk/commands/lint/templates/dockerfile.jinja2

        Args:
            docker_base_image(str): docker image to use as base for installing dev deps.
            no_test(bool): wheter to run tests or not - will install required packages if True.

        Returns:
            string. image name to use
        """
        log_prompt = f"{self._pack_name} - Image create"
        test_image_id = ""
        # Get requirements file for image
        if 2 < docker_base_image[1] < 3:
            requirements = self._req_2
        elif docker_base_image[1] > 3:
            requirements = self._req_3
        else:
            requirements = []
        # Using DockerFile template
        file_loader = FileSystemLoader(Path(__file__).parent / 'templates')
        env = Environment(loader=file_loader, lstrip_blocks=True, trim_blocks=True)
        template = env.get_template('dockerfile.jinja2')
        try:
            dockerfile = template.render(image=docker_base_image[0],
                                         pypi_packs=requirements + self._facts["additional_requirements"],
                                         no_test=(self._facts["test"] and no_test),
                                         pack_type=self._pkg_lint_status["pack_type"],
                                         update_certs=True if self._facts["env_vars"]["DEMISTO_LINT_UPDATE_CERTS"] == "yes"
                                         else False)
        except exceptions.TemplateError as e:
            logger.debug(f"{log_prompt} - Error when build image - {e.message()}")
            return test_image_id, str(e)
        # Trying to pull image based on dockerfile hash, will check if something changed
        errors = ""
        test_image_name = f'devtest{docker_base_image[0]}-{hashlib.md5(dockerfile.encode("utf-8")).hexdigest()}'
        test_image = None
        try:
            logger.info(f"{log_prompt} - trying to pull existing image {test_image_name}")
            test_image = self._docker_client.images.pull(test_image_name)
        except (docker.errors.APIError, docker.errors.ImageNotFound):
            logger.info(f"{log_prompt} - Unable to find image {test_image_name}")
        # Creatng new image if existing image isn't found
        if not test_image:
            logger.info(f"{log_prompt} - Creating image based on {docker_base_image[0]}")
            certificate_path = Path(__file__).parent / 'resources' / 'certificates'
            with tempfile.NamedTemporaryFile(dir=certificate_path, suffix=".Dockerfile") as fp:
                fp.write(dockerfile.encode("utf-8"))
                fp.seek(0)
                try:
                    test_image = self._docker_client.images.build(path=str(certificate_path),
                                                                  dockerfile=fp.name,
                                                                  tag=test_image_name,
                                                                  forcerm=True,
                                                                  quiet=True)
                    if self._docker_hub_login and test_image:
                        for trial in range(2):
                            try:
                                self._docker_client.images.push(test_image_name,
                                                                stream=False)
                            except (requests.exceptions.ConnectionError, urllib3.exceptions.ReadTimeoutError):
                                logger.info(f"{log_prompt} - Image {test_image_name} pushed to repository")
                except (docker.errors.BuildError, docker.errors.APIError) as e:
                    logger.critical(f"{log_prompt} - build errors occured {e}")
                    errors = str(e)
        else:
            logger.info(f"{log_prompt} - found existing image {test_image_name}")

        for trial in range(2):
            try:
                container_obj = self._docker_client.containers.create(image=test_image_name)
                copy_dir_to_container(container_obj=container_obj,
                                      host_path=self._pack_abs_dir,
                                      container_path=Path('/devwork'))
                test_image_id = container_obj.commit().short_id
                container_obj.remove()
            except (docker.errors.ImageNotFound, docker.errors.APIError, urllib3.exceptions.ReadTimeoutError) as e:
                logger.info(f"{log_prompt} - errors occured when copy pack dir {e}")
                if trial == 2:
                    errors = str(e)
        if test_image_id:
            logger.info(f"{log_prompt} - Image {test_image_id} created succefully")

        return test_image_id, errors

    def _docker_run_pylint(self, test_image: str, keep_container: bool) -> Tuple[int, str]:
        """ Run Pylint in container based to created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after excution finished

        Returns:
            int: 0 on successful, errors 1, neet to retry 2
            str: Container log
        """
        log_prompt = f'{self._pack_name} - Pylint - Image {test_image}'
        logger.info(f"{log_prompt} - Start")
        container_name = f"{self._pack_name}-pylint"
        # Check if previous run left container a live if it do, we remove it
        container_obj: docker.models.containers.Container
        try:
            container_obj = self._docker_client.containers.get(container_name)
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Run container
        exit_code = 0b0
        output = ""
        try:
            container_obj = self._docker_client.containers.run(name=container_name,
                                                               image=test_image,
                                                               command=[build_pylint_command(self._facts["lint_files"])],
                                                               user=f"{os.getuid()}:4000",
                                                               detach=True,
                                                               environment=self._facts["env_vars"])
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.debug(f"{log_prompt} - exit-code: {container_exit_code}")
            logger.debug(f"{log_prompt} - container output:{RL if container_log else ''}{container_log}")
            if container_exit_code in [1, 2]:
                # 1-fatal message issued
                # 2-Error message issued
                exit_code = 0b1
                output = container_log
                logger.info(f"{log_prompt} - Finished errors found")
            elif container_exit_code in [4, 8, 16]:
                # 4-Warning message issued
                # 8-refactor message issued
                # 16-convention message issued
                logger.info(f"{log_prompt} - Finshed success - warnings found")
                exit_code = 0b0
            elif container_exit_code == 32:
                # 32-usage error
                logger.critical(f"{log_prompt} - Finished - Usage error")
                exit_code = 0b10
            else:
                logger.info(f"{log_prompt} - Finished success")
            # Keeping container if needed or remove it
            if keep_container:
                print(f"{log_prompt} - container name {container_name}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to delete container - {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{log_prompt} - Unable to run pylint - {e}")
            exit_code = 0b10
            output = str(e)

        return exit_code, output

    def _docker_run_pytest(self, test_image: str, keep_container: bool, test_xml: str) -> Tuple[int, str]:
        """ Run Pylint in container based to created test image

        Args:
            test_image(str): Test image id/name
            keep_container(bool): True if to keep container after excution finished
            test_xml(str): Xml saving path

        Returns:
            int: 0 on successful, errors 1, neet to retry 2
            str: Unit test json report
        """
        log_prompt = f'{self._pack_name} - Pytest - Image {test_image}'
        logger.info(f"{log_prompt} - Start")
        container_name = f"{self._pack_name}-pytest"
        # Check if previous run left container a live if it does, Remove it
        container_obj: docker.models.containers.Container
        try:
            container_obj = self._docker_client.containers.get(container_name)
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass
        # Collect tests
        exit_code = 0b0
        test_json = {}
        try:
            # Running pytest container
            container_obj = self._docker_client.containers.run(name=container_name,
                                                               image=test_image,
                                                               command=[build_pytest_command(test_xml=test_xml, json=True)],
                                                               user=f"{os.getuid()}:4000",
                                                               detach=True,
                                                               environment=self._facts["env_vars"])
            # Waiting for container to be finished
            container_status: dict = container_obj.wait(condition="exited")
            # Getting container exit code
            container_exit_code: int = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.debug(f"{log_prompt} - exit-code: {container_exit_code}")
            logger.debug(f"{log_prompt} - container output: {RL if container_log else ''}{container_log}")
            if container_exit_code in [0, 1, 2, 5]:
                # 0-All tests passed
                # 1-Tests were collected and run but some of the tests failed
                # 2-Test execution was interrupted by the user
                # 5-No tests were collected
                if test_xml:
                    test_data_xml: bytes = get_file_from_container(container_obj=container_obj,
                                                                   container_path="/devwork/report_pytest.xml")
                    xml_apth = Path(test_xml) / f'{self._pack_name}_pytest.xml'
                    with open(file=xml_apth, mode='bw') as f:
                        f.write(test_data_xml)

                test_json: dict = json.loads(get_file_from_container(container_obj=container_obj,
                                                                     container_path="/devwork/report_pytest.json",
                                                                     encoding="utf-8"))
                for test in test_json.get('report', {}).get("tests"):
                    if test.get("call", {}).get("longrepr"):
                        test["call"]["longrepr"] = test["call"]["longrepr"].split('\n')
                if container_exit_code in [0, 5]:
                    logger.info(f"{log_prompt} - Finished success")
                    exit_code = 0b0
                else:
                    logger.info(f"{log_prompt} - Finished errors found")
                    exit_code = 0b1
            elif container_exit_code in [3, 4]:
                # 3-Internal error happened while executing tests
                # 4-pytest command line usage error
                logger.critical(f"{log_prompt} - Usage error")
                exit_code = 0b10
            # Remove container if not needed
            if keep_container:
                print(f"{log_prompt} - Conatiner name {container_name}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{log_prompt} - Unable to remove container {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{log_prompt} - Unable to run pytest container {e}")
            exit_code = 0b10

        return exit_code, test_json

    def _docker_run_pwsh_analyze(self, test_image: str, keep_container: bool) -> Tuple[int, str]:
        """ Run Powershell code analyze in container based to created test image

        Args:
            test_image(str): test image id/name
            keep_container(bool): True if to keep container after excution finished

        Returns:
            int: 0 on successful, errors 1, neet to retry 2
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
        exit_code = 0b0
        output = ""
        try:
            container_obj = self._docker_client.containers.run(name=container_name,
                                                               image=test_image,
                                                               command=[build_pwsh_analyze_command(self._facts["lint_files"])],
                                                               user=f"{os.getuid()}:4000",
                                                               detach=True,
                                                               environment=self._facts["env_vars"])
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.debug(f"{log_prompt} - exit-code: {container_exit_code}")
            logger.debug(f"{log_prompt} - container output:{RL if container_log else ''}{container_log}")
            if container_exit_code:
                # 1-fatal message issued
                # 2-Error message issued
                logger.info(f"{log_prompt} - Finshed errors found")
                output = container_log
                exit_code = 0b1
            else:
                logger.info(f"{log_prompt} - Finished success")
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
            exit_code = 0b10

        return exit_code, output

    def _docker_run_pwsh_test(self, test_image: str, keep_container: bool) -> Tuple[int, str]:
        """ Run Powershell tests in container based to created test image

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
        container_obj: docker.models.containers.Container
        try:
            container_obj = self._docker_client.containers.get(container_name)
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Run container
        exit_code = 0b0
        output = ""
        try:
            container_obj = self._docker_client.containers.run(name=container_name,
                                                               image=test_image,
                                                               command=[build_pwsh_test_command()],
                                                               user=f"{os.getuid()}:4000",
                                                               detach=True,
                                                               environment=self._facts["env_vars"])
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            # Getting container logs
            container_log = container_obj.logs().decode("utf-8")
            logger.debug(f"{log_prompt} - exit-code: {container_exit_code}")
            logger.debug(f"{log_prompt} - container output:{RL if container_log else ''}{container_log}")
            if container_exit_code:
                # 1-fatal message issued
                # 2-Error message issued
                logger.info(f"{log_prompt} - Finshed errors found")
                output = container_log
                exit_code = 0b1
            else:
                logger.info(f"{log_prompt} - Finished success")
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
            exit_code = 0b10

        return exit_code, output

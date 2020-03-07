# STD python packages
import logging
from typing import Tuple, List, Optional
import tempfile
import os
import json
# 3-rd party packages
import docker.errors
import docker.models.containers
import docker
from jinja2 import Environment, FileSystemLoader, exceptions
from ruamel.yaml import YAML
from wcmatch.pathlib import Path, BRACE, NEGATE
# Local packages
from demisto_sdk.commands.common.tools import get_all_docker_images
from demisto_sdk.commands.lint.commands_builder import build_mypy_command, build_bandit_command, build_pytest_command, \
    build_pylint_command, build_flake8_command, build_vulture_command
from demisto_sdk.commands.lint.helpers import get_file_from_container, get_python_version_from_image, \
    run_command_os, create_tmp_lint_files

FAIL_EXIT_CODES = {
    "flake8": 0b1,
    "bandit": 0b10,
    "mypy": 0b100,
    "vulture": 0b1000000,
    "pytest": 0b1000,
    "pylint": 0b10000,
    "image": 0b100000
}

logger = logging.getLogger('demisto-sdk')


class Linter:
    """ Linter used to activate lint command on single package

        Attributes:
            pack_dir(Path): Pack to run lint on.
            req_2(list): requirements for docker using python2
            req_3(list): requirements for docker using python3
    """

    def __init__(self, pack_dir: Path, content_path: Path, req_3: list, req_2: list):
        self._req_3 = req_3
        self._req_2 = req_2
        self._content_path = content_path
        self._pack_rel_dir = pack_dir
        self._pack_abs_dir = self._content_path / pack_dir
        self._pack_name = pack_dir.name
        # Docker client init
        self._docker_client: docker.DockerClient = docker.from_env()
        # Facts gathered regarding pack lint and test
        self._facts = {
            "images": [],
            "python_pack": False,
            "test": False,
            "version_two": False,
            "lint_files": [],
            "additional_requirements": []
        }
        # Pack lint status object - visualize it
        self._pkg_lint_status = {
            "pkg": self._pack_name,
            "path": str(self._pack_rel_dir),
            "images": [],
            "flake8_errors": None,
            "bandit_errors": None,
            "mypy_errors": None,
            "exit_code": 0
        }

    def run_dev_packages(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool, no_vulture: bool,
                         no_test: bool, modules: dict, keep_container: bool, test_xml: str) -> Tuple[int, dict]:
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
            modules(dict): Mandatory modules to locate in pack path (CommonServerPython.py etc)
            keep_container(bool): Whether to keep the test container
            test_xml(str): Path for saving pytest xml results

        Returns:
            int: exit code 0 if all succeed else 1
            dict: lint and test all status, pkg status)
        """
        # Gather information for lint check information
        self._gather_facts(modules)
        # If not python pack - skip pack
        if not self._facts["python_pack"]:
            return 0b0, self._pkg_lint_status

        # Locate mandatory files in pack path - for more info checkout the context manager LintFiles
        with create_tmp_lint_files(content_path=self._content_path,
                                   pack_path=self._pack_abs_dir,
                                   lint_files=self._facts["lint_files"],
                                   modules=modules,
                                   version_two=self._facts["version_two"]) as lint_files:
            # If temp files created for lint check - replace them
            self._facts["lint_files"]: List[Path] = lint_files
            # Run lint check on host - flake8, bandit, mypy
            self._run_lint_in_host(no_flake8=no_flake8,
                                   no_bandit=no_bandit,
                                   no_mypy=no_mypy,
                                   no_vulture=no_vulture)
            # Run lint and test check on pack docker image
            self._run_lint_on_docker_image(no_pylint=no_pylint,
                                           no_test=no_test,
                                           keep_container=keep_container,
                                           test_xml=test_xml)

        return self._pkg_lint_status["exit_code"], self._pkg_lint_status

    def _gather_facts(self, modules) -> object:
        """ Gathering facts about the package - python version, docker images, vaild docker image, yml parsing

        Returns:
            pkg lint status, python version, docker images, indicate if docker image valid,
            indicate if pack is python pack
        """
        # Loading pkg yaml
        yml_file: Optional[Path] = next(self._pack_abs_dir.glob(rf'{self._pack_name}.{{yml,yaml}}', flags=BRACE), None)
        if not yml_file:
            logger.info(f"{self._pack_name} - Facts - Skiping no yaml file found {yml_file}")
            return
        logger.info(f"{self._pack_name} - Facts -  Using yaml file {yml_file}")

        # Parsing pack yaml - inorder to verify if check needed
        yml_obj: dict = YAML().load(yml_file)
        script_obj: dict = yml_obj if 'script' not in yml_obj.keys() else yml_obj.get('script', {})
        pack_type = script_obj.get('type')

        # return no check needed if not python pack
        if not pack_type == 'python':
            logger.info(f"{self._pack_name} - Facts - Not Python package")
            return
        self._facts["python_pack"] = True
        logger.info(f"{self._pack_name} - Facts - Python package")

        # Getting python version from docker image - verfying if not valid docker image configured
        for image in get_all_docker_images(script_obj=script_obj):
            py_num: float = get_python_version_from_image(image=image)
            self._facts["images"].append([image, py_num])
            logger.info(f"{self._pack_name} - Facts - {image} - Python {py_num}")
            if py_num < 3:
                self._facts["version_two"] = True

        # Checking wheter *test* exsits in package
        self._facts["test"] = True if next(self._pack_abs_dir.glob([r'test_*.py', r'*_test.py']), None) else False
        if self._facts["test"]:
            logger.info(f"{self._pack_name} - Facts - Tests found")

        # Get lint files
        lint_files = set(self._pack_abs_dir.glob(["*.py", "!*_test.py", "!test_*.py", "!__init__.py"], flags=NEGATE))
        test_modules = {self._pack_abs_dir / k for k in modules.keys()}
        lint_files = lint_files.difference(test_modules)
        self._facts["lint_files"] = list(lint_files)
        for lint_file in lint_files:
            logger.info(f"{self._pack_name} - Facts - Lint files {lint_file}")

        # Gather package requirements embeded test-requirements.py file
        test_requirements = self._pack_abs_dir / 'test-requirements.txt'
        if test_requirements.exists():
            additional_req = test_requirements.read_text(encoding='utf-8')
            self._facts["additinal_requirements"].extend(additional_req)
            logger.debug(f"{self._pack_name} - Facts - Additional package Pypi packages found - {additional_req}")

    def _run_lint_in_host(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_vulture: bool):
        """ Run lint check on host

        Args:
            no_flake8: Whether to skip flake8.
            no_bandit: Whether to skip bandit.
            no_mypy: Whether to skip mypy.
        """
        if self._facts["lint_files"]:
            for lint_check in ["flake8", "bandit", "mypy", "vulture"]:
                exit_code: int = 0b0
                output: str = ""
                if lint_check == "flake8" and not no_flake8:
                    exit_code, output = self._run_flake8(lint_files=self._facts["lint_files"])
                elif lint_check == "bandit" and not no_bandit:
                    exit_code, output = self._run_bandit(lint_files=self._facts["lint_files"])
                elif lint_check == "mypy" and not no_mypy and self._facts["images"][0]:
                    exit_code, output = self._run_mypy(py_num=self._facts["images"][0][1],
                                                       lint_files=self._facts["lint_files"])
                elif lint_check == "vulture" and not no_vulture:
                    exit_code, output = self._run_vulture(lint_files=self._facts["lint_files"])
                if exit_code:
                    self._pkg_lint_status["exit_code"] += FAIL_EXIT_CODES[lint_check]
                    self._pkg_lint_status[f"{lint_check}_errors"] = output

    def _run_flake8(self, lint_files: List[Path]) -> Tuple[int, str]:
        """ Runs flake8 in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Flake8 - Start")
        stdout, stderr, exit_code = run_command_os(command=build_flake8_command(lint_files),
                                                   cwd=self._pack_abs_dir)
        if stderr:
            return 1, stderr
        elif not exit_code:
            logger.info(f"{self._pack_name} - Flake8 - Finshed success")
            return 0, ""

        logger.info(f"{self._pack_name} - Flake8 - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Flake8 - Finshed  errors - {stdout}")

        return 1, stdout

    def _run_bandit(self, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run bandit in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Bandit - Start")
        stdout, stderr, exit_code = run_command_os(command=build_bandit_command(lint_files),
                                                   cwd=self._pack_abs_dir)

        if stderr:
            return 1, stderr
        elif not exit_code:
            logger.info(f"{self._pack_name} - Bandit - Finshed success")
            return 0, ""

        logger.info(f"{self._pack_name} - Bandit - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Bandit - Finshed  errors - {stdout}")

        return 1, stdout

    def _run_mypy(self, py_num: float, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run mypy in pack dir

        Args:
            py_num(float): The python version in use
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Mypy - Start")
        stdout, stderr, exid_code = run_command_os(command=build_mypy_command(files=lint_files, version=py_num),
                                                   cwd=self._pack_abs_dir)
        if stderr:
            return 1, stderr
        elif not exid_code:
            logger.info(f"{self._pack_name} - Mypy - Finshed success")
            return 0, ""

        logger.info(f"{self._pack_name} - Mypy - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Mypy - Finshed  errors - {stdout}")

        return 1, stdout

    def _run_vulture(self, lint_files: List[Path]) -> Tuple[int, str]:
        """ Run mypy in pack dir

        Args:
            lint_files(List[Path]): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Vulture - Start")
        stdout, stderr, exid_code = run_command_os(command=build_vulture_command(files=lint_files,
                                                                                 pack_path=self._pack_abs_dir),
                                                   cwd=self._pack_abs_dir)
        if stderr:
            return 1, stderr
        elif not exid_code:
            logger.info(f"{self._pack_name} - Vulture - Finshed success")
            return 0, ""

        logger.info(f"{self._pack_name} - Vulture - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Vulture - Finshed  errors - {stdout}")

        return 1, stdout

    def _run_lint_on_docker_image(self, no_pylint: list, no_test: bool, keep_container: bool, test_xml: str):
        """ Run lint check on docker image

        Args:
            no_pylint(bool): Whether to skip pylint.
            no_test(bool): Whether to skip pytest.
            keep_container(bool): Whether to keep the test container.
            test_xml(str): Path for saving pytest xml results.
        """
        for image in self._facts["images"]:
            # Give each image 2 tries, if first failed willl validate second time
            for trial in range(2):
                need_to_retry = False
                # Docker image status - visualize
                status = {
                    "image": image[0],
                    "image_errors": None,
                    "pylint_errors": None,
                    "pytest_json": {}
                }
                # Creating image if pylint specifie or found tests and tests specified
                docker_image_created, errors = self._docker_image_create(docker_base_image=image,
                                                                         no_test=no_test)
                if docker_image_created:
                    # Set image creation status
                    for check in ["pylint", "pytest"]:
                        # Perform pylint
                        if not no_pylint and check == "pylint" and self._facts["lint_files"]:
                            exit_code, output = self._docker_run_pylint(test_image=docker_image_created,
                                                                        keep_container=keep_container)
                            if exit_code:
                                self._pkg_lint_status["exit_code"] += FAIL_EXIT_CODES["pylint"]
                                status[f"{check}_errors"] = output
                                if exit_code in [32]:
                                    need_to_retry = True
                        # Perform pytest
                        elif not no_test and self._facts["test"] and check == "pytest":
                            exit_code, test_json = self._docker_run_pytest(test_image=docker_image_created,
                                                                           keep_container=keep_container,
                                                                           test_xml=test_xml)
                            status["pytest_json"]: dict = test_json
                            if exit_code:
                                self._pkg_lint_status["exit_code"] += FAIL_EXIT_CODES["pytest"]
                                if exit_code in [3, 4]:
                                    need_to_retry = True
                elif trial == 0:
                    need_to_retry = True
                elif trial == 1:
                    status["image_errors"] = str(errors)
                    self._pkg_lint_status["exit_code"] += FAIL_EXIT_CODES["image"]

                if not need_to_retry:
                    self._pkg_lint_status["images"].append(status)
                    break

    def _docker_image_create(self, docker_base_image: str, no_test: bool) -> str:
        """ Create docker image:
            1. Installing build base if required in alpine images version - https://wiki.alpinelinux.org/wiki/GCC
            2. Installing pypi packs - if only pylint required - only pylint installed otherwise all pytest and pylint
               installed, packages which being install can be found in path demisto_sdk/commands/lint/dev_envs
            3. The docker image build done by Dockerfile template located in
                demisto_sdk/commands/lint/templates/dockerfile.jinja2

        Args:
            docker_base_image(str): docker image to use as base for installing dev deps.
            no_test(bool): wheter to run tests or not - will install required packages if True.

        Returns:
            str: image short uniq ID
        """
        test_image_id = ""
        logger.info(f"{self._pack_name} - Image build - Creating image based on {docker_base_image[0]}")
        # Using DockerFile template
        file_loader = FileSystemLoader(Path(__file__).parent / 'templates')
        env = Environment(loader=file_loader, trim_blocks=True, lstrip_blocks=True)
        template = env.get_template('dockerfile.jinja2')
        if docker_base_image[1] < 3:
            requirements = self._req_2
        else:
            requirements = self._req_3
        try:
            dockerfile = template.render(image=docker_base_image[0],
                                         pypi_packs=requirements + self._facts["additional_requirements"],
                                         project_dir=str(self._pack_abs_dir),
                                         circle_ci=os.getenv("CI", False),
                                         no_test=(self._facts["test"] and no_test))
        except exceptions.TemplateError as e:
            return test_image_id, str(e)
        # Try 3 times creating image - error occures with communicating with docker API
        errors = ""
        for trial in range(2):
            try:
                # Building test image
                with tempfile.NamedTemporaryFile(dir=self._pack_abs_dir, suffix=".Dockerfile") as fp:
                    fp.write(dockerfile.encode("utf-8"))
                    fp.seek(0)
                    test_image = self._docker_client.images.build(path=str(self._pack_abs_dir),
                                                                  dockerfile=fp.name,
                                                                  tag=docker_base_image[0] + "-test",
                                                                  rm=True)
                    test_image_id = test_image[0].short_id
                break
            except (docker.errors.BuildError, docker.errors.APIError) as e:
                logger.critical(f"{self._pack_name} - Image build - errors occured {e}")
                if trial == 1:
                    errors = e

        if test_image_id:
            logger.info(f"{self._pack_name} - Image build -  Image {test_image_id} created succefully")

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
        logger.info(f"{self._pack_name} - Pylint - Image {test_image} - Start")
        pylint_command: str = build_pylint_command(self._facts["lint_files"])
        # Check if previous run left container a live if it do, we remove it
        container_obj: docker.models.containers.Container
        try:
            container_obj = self._docker_client.containers.get(f"{self._pack_name}-pylint")
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass

        # Run container
        container_log = ""
        try:
            container_obj = self._docker_client.containers.run(name=f"{self._pack_name}-pylint",
                                                               image=test_image,
                                                               command=[pylint_command],
                                                               detach=True,
                                                               user=f"{os.getuid()}:4000")
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            if container_exit_code in [1, 2]:
                # 1-fatal message issued
                # 2-Error message issued
                logger.info(f"{self._pack_name} - Pylint - Image {test_image} - Finshed errors found")
                container_log = container_obj.logs().decode("utf-8")
                container_exit_code = 1
            elif container_exit_code in [4, 8, 16]:
                # 4-Warning message issued
                # 8-refactor message issued
                # 16-convention message issued
                logger.warning(f"{self._pack_name} - Pylint - Image {test_image} - Finshed success - warnings found")
                container_exit_code = 0
            elif container_exit_code == 32:
                # 32-usage error
                logger.critical(f"{self._pack_name} - Pylint - Image {test_image} - Finished- Usage error")
                return 2, container_log

            # Keeping container if needed or remove it
            if keep_container:
                print(f"{self._pack_name} - Pylint - Image {test_image} - container name"
                      f" {self._pack_name}-pylint")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(
                        f"{self._pack_name} - Pylint - Image {test_image} - Unable to delete container - {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{self._pack_name} - Pylint - Image {test_image} - Unable to run pylint - {e}")
            return 2, container_log

        if container_exit_code:
            logger.info(f"{self._pack_name} - Pylint - Image {test_image} - Finished errors found")
        else:
            logger.info(f"{self._pack_name} - Pylint - Image {test_image} - Finished success")

        return container_exit_code, container_log

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
        logger.info(f"{self._pack_name} - Pytest -  Image {test_image} - Start")
        pytest_command: str = build_pytest_command(test_xml=test_xml,
                                                   json=True)
        # Check if previous run left container a live if it does, Remove it
        container_obj: docker.models.containers.Container
        try:
            container_obj = self._docker_client.containers.get(f"{self._pack_name}-pytest")
            container_obj.remove(force=True)
        except docker.errors.NotFound:
            pass
        # Collect tests
        test_json = {}
        try:
            # Running pytest container
            container_obj = self._docker_client.containers.run(name=f"{self._pack_name}-pytest",
                                                               image=test_image,
                                                               command=[pytest_command],
                                                               user=f"{os.getuid()}:4000",
                                                               detach=True)
            # Waiting for container to be finished
            container_status: dict = container_obj.wait(condition="exited")
            # Getting container exit code
            container_exit_code: int = container_status.get("StatusCode")
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
                for i in range(len(test_json.get('report', {}).get("tests"))):
                    if test_json['report']["tests"][i]["call"].get("longrepr"):
                        test_json['report']["tests"][i]["call"]["longrepr"] = test_json['report']["tests"][i]["call"][
                            "longrepr"].split('\n')
                if container_exit_code == 5:
                    container_exit_code = 0
            elif container_exit_code in [3, 4]:
                # 3-Internal error happened while executing tests
                # 4-pytest command line usage error
                logger.critical(f"{self._pack_name} - Pytest - Image {test_image} - Usage error")
                return 2, test_xml
            # Remove container if not needed
            if keep_container:
                print(f"{self._pack_name} - Pytest - Image {test_image} - conatiner name "
                      f"{self._pack_name}-pytest")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{self._pack_name} - Pytest - Image {test_image} - Unable to remove container {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{self._pack_name} - Pytest - Image {test_image} - Unable to run pytest container {e}")
            return 2, test_json

        if container_exit_code:
            logger.info(f"{self._pack_name} - Pytest - Image{test_image} - Finished errors found")
        else:
            logger.info(f"{self._pack_name} - Pytest - Image {test_image} - Finished success")

        return container_exit_code, test_json

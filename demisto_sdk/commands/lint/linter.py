# STD python packages
import logging
from typing import Tuple
import yaml
import glob
import os
import tempfile
import json
# 3-rd party packages
import docker.errors
import docker.models.containers
import docker
from jinja2 import Environment, FileSystemLoader
# Local packages
from demisto_sdk.commands.common.tools import get_all_docker_images, get_yml_paths_in_dir, run_command
from demisto_sdk.commands.lint.commands_builder import build_mypy_command, build_bandit_command, build_pytest_command, \
    build_pylint_command, build_flake8_command
from demisto_sdk.commands.lint.helpers import get_file_from_container, LintFiles, get_python_version_from_image

FAIL_EXIT_CODES = {
    "flake8": 0b1,
    "bandit": 0b10,
    "mypy": 0b100,
    "pytest": 0b1000,
    "pylint": 0b10000,
    "image": 0b100000
}

logger = logging.getLogger('demisto-sdk')


class Linter:
    """ Linter used to activate lint command on single package

        Attributes:
            pack_dir(str): Pack to run lint on.
            req_2(list): requirements for docker using python2
            req_3(list): requirements for docker using python3
    """

    def __init__(self, pack_dir: str, content_path: str, req_3: list, req_2: list):
        self._req_3 = req_3
        self._req_2 = req_2
        self._content_path = content_path
        self._pack_rel_dir = pack_dir
        self._pack_abs_dir = os.path.abspath(os.path.join(self._content_path, pack_dir))
        self._pack_name = os.path.basename(pack_dir)
        # Docker client init
        self._docker_client: docker.DockerClient = docker.from_env()
        # Facts gathered regarding pack lint and test
        self._facts = {
            "images": [],
            "python_pack": True,
            "test": False,
            "version_two": False,
            "lint_files": [],
            "additional_requirements": []
        }
        # Pack lint status object - visualize it
        self._pkg_lint_status = {
            "pkg": self._pack_name,
            "path": self._pack_rel_dir,
            "images": [],
            "flake8_errors": None,
            "bandit_errors": None,
            "mypy_errors": None,
            "exit_code": 0
        }

    def run_dev_packages(self, no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool, no_test: bool,
                         modules: dict, keep_container: bool, test_xml: str) -> Tuple[int, dict]:
        """ Run lint and tests on single package
        Perfroming the follow:
            1. Run the lint on OS - flake8, bandit, mypy.
            2. Run in package docker - pylint, pytest.

        Args:
            no_flake8(bool): Whether to skip flake8
            no_bandit(bool): Whether to skip bandit
            no_mypy(bool): Whether to skip mypy
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
        try:
            with LintFiles(pack_path=self._pack_abs_dir,
                           lint_files=self._facts["lint_files"],
                           modules=modules,
                           content_path=self._content_path,
                           version_two=self._facts["version_two"]) as lint_files:
                # If temp files created for lint check - replace them
                self._facts["lint_files"] = lint_files
                # Run lint check on host - flake8, bandit, mypy
                self._run_lint_on_host(no_flake8=no_flake8,
                                       no_bandit=no_bandit,
                                       no_mypy=no_mypy)
                # Run lint and test check on pack docker image
                self._run_lint_on_docker_image(no_pylint=no_pylint,
                                               no_test=no_test,
                                               keep_container=keep_container,
                                               test_xml=test_xml)
        except IOError:
            pass

        return self._pkg_lint_status["exit_code"], self._pkg_lint_status

    def _gather_facts(self, modules) -> object:
        """ Gathering facts about the package - python version, docker images, vaild docker image, yml parsing

        Returns:
            pkg lint status, python version, docker images, indicate if docker image valid,
            indicate if pack is python pack
        """
        # Loading pkg yaml
        _, yml_path = get_yml_paths_in_dir(self._pack_abs_dir, "")
        if not yml_path:
            logger.info(f"{self._pack_name} - Facts - Skiping no yaml file found {yml_path}")
        logger.info(f"{self._pack_name} - Facts -  Using yaml file {yml_path}")

        # Parsing pack yaml - inorder to verify if check needed
        script_obj: dict = {}
        with open(yml_path, mode='rt', encoding='utf-8') as yml_file:
            script_obj = yaml.safe_load(yml_file)
        if isinstance(script_obj.get('script'), dict):
            script_obj = script_obj.get('script')
        script_type = script_obj.get('type')

        # return no check needed if not python pack
        if script_type != 'python':
            self._facts["python_pack"] = False
            logger.info(f"{self._pack_name} - Facts - Skipping due to not python pack by yaml")
            return
        logger.info(f"{self._pack_name} - Facts - Python package")

        # Getting python version from docker image - verfying if not valid docker image configured
        for image in get_all_docker_images(script_obj=script_obj):
            py_num = get_python_version_from_image(image=image)
            self._facts["images"].append([image, py_num])
            logger.info(f"{self._pack_name} - Facts - {image} - Python {py_num}")
            if '2.' in py_num:
                self._facts["version_two"] = True

        # Checking wheter *test* exsits in package
        type_1 = glob.glob(f"{self._pack_abs_dir}/*_test.py")
        type_2 = glob.glob(f"{self._pack_abs_dir}/test_*.py")
        if type_1 or type_2:
            self._facts["test"] = True
            logger.info(f"{self._pack_name} - Facts - Tests found")

        # Get lint files
        lint_files = glob.glob(f"{self._pack_abs_dir}/*.py")
        for k, v in modules.items():
            file_path = os.path.join(f"{self._pack_abs_dir}", k)
            if file_path in lint_files:
                if self._pack_name != "CommonServerPython":
                    lint_files.remove(file_path)
                else:
                    if k != "CommonServerPython.py":
                        lint_files.remove(file_path)
        lint_files = (set(lint_files).difference(type_1)).difference(type_2)
        self._facts["lint_files"] = list(lint_files)
        logger.info(f"{self._pack_name} - Facts - Lint files {self._facts['lint_files']}")

        # Gather package requirements embeded test-requirements.py file
        try:
            test_requirements_path = os.path.join(self._pack_abs_dir, 'test-requirements.txt')
            if os.path.exists(test_requirements_path):
                with open(file=test_requirements_path) as f:
                    additional_req = f.readlines()
                    self._facts["additinal_requirements"].extend(additional_req)
                    logger.debug(f"{self._pack_name} - Facts - Additional package Pypi packages found "
                                 f"- {additional_req}")
        except (FileNotFoundError, IOError) as e:
            logger.critical(f"{self._pack_name} - Facts - requirments gather - {e}")

    def _run_lint_on_host(self, no_flake8: bool, no_bandit: bool, no_mypy: bool):
        """ Run lint check on host

        Args:
            no_flake8: Whether to skip flake8.
            no_bandit: Whether to skip bandit.
            no_mypy: Whether to skip mypy.
        """
        for lint_check in ["flake8", "bandit", "mypy"]:
            exit_code: int = 0b0
            output: str = ""
            if lint_check == "flake8" and not no_flake8:
                exit_code, output = self._run_flake8(lint_files=self._facts["lint_files"])
            elif lint_check == "bandit" and not no_bandit:
                exit_code, output = self._run_bandit(lint_files=self._facts["lint_files"])
            elif lint_check == "mypy" and not no_mypy and self._facts["images"][0]:
                exit_code, output = self._run_mypy(py_num=self._facts["images"][0][1],
                                                   lint_files=self._facts["lint_files"])
            if exit_code:
                self._pkg_lint_status["exit_code"] += FAIL_EXIT_CODES[lint_check]
                self._pkg_lint_status[f"{lint_check}_errors"] = output

    def _run_flake8(self, lint_files: list) -> Tuple[int, str]:
        """ Runs flake8 in pack dir

        Args:
            lint_files(list): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Flake8 - Start")
        output: str = run_command(command=build_flake8_command(lint_files),
                                  cwd=self._pack_abs_dir)

        if len(output) == 0:
            logger.info(f"{self._pack_name} - Flake8 - Finshed success")
            return 0, ""

        logger.error(f"{self._pack_name} - Flake8 - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Flake8 - Finshed  errors - {output}")

        return 1, output

    def _run_bandit(self, lint_files: list) -> Tuple[int, str]:
        """ Run bandit in pack dir

        Args:
            lint_files(list): file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Bandit - Start")
        output: str = run_command(command=build_bandit_command(lint_files),
                                  universal_newlines=False,
                                  cwd=self._pack_abs_dir)

        if len(output) == 0:
            logger.info(f"{self._pack_name} - Bandit - Finshed success")
            return 0, ""

        logger.error(f"{self._pack_name} - Bandit - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Bandit - Finshed  errors - {output}")

        return 1, output

    def _run_mypy(self, py_num: float, lint_files: list) -> Tuple[int, str]:
        """ Run mypy in pack dir

        Args:
            py_num: The python version in use
            lint_files: file to perform lint

        Returns:
           int:  0 on successful else 1, errors
           str: Bandit errors
        """
        logger.info(f"{self._pack_name} - Mypy - Start")
        output: str = run_command(command=build_mypy_command(lint_files, version=py_num),
                                  universal_newlines=False,
                                  cwd=self._pack_abs_dir)
        if 'Success: no issues found' in output:
            logger.info(f"{self._pack_name} - Mypy - Finshed success")
            return 0, ""

        logger.error(f"{self._pack_name} - Mypy - Finshed Finshed errors found")
        logger.debug(f"{self._pack_name} - Mypy - Finshed  errors - {output}")

        return 1, output

    def _run_lint_on_docker_image(self, no_pylint: list, no_test: bool, keep_container: bool, test_xml: str):
        """ Run lint check on docker image

        Args:
            no_pylint(bool): Whether to skip pylint.
            no_test(bool): Whether to skip pytest.
            keep_container(bool): Whether to keep the test container.
            test_xml(str): Path for saving pytest xml results.
        """
        image: str
        for image in self._facts["images"]:
            # Give each image 2 tries, if first failed willl validate second time
            for trial in range(2):
                logger.info(f"{self._pack_name} - Using Image {image[0]} - Python {image[1]}")
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
                        if not no_pylint and check == "pylint":
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
                            status["pytest_json"] = test_json
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
        test_image_id: str = ""
        logger.info(f"{self._pack_name} - Creating image based on {docker_base_image[0]}")
        # Using DockerFile template
        file_loader = FileSystemLoader(f'{os.path.dirname(__file__)}/templates')
        env = Environment(loader=file_loader, trim_blocks=True, lstrip_blocks=True)
        template = env.get_template('dockerfile.jinja2')
        if '2.' in docker_base_image[1]:
            requirements = self._req_2
        else:
            requirements = self._req_3
        dockerfile = template.render(image=docker_base_image[0],
                                     pypi_packs=requirements + self._facts["additional_requirements"],
                                     project_dir=self._pack_abs_dir,
                                     circle_ci=os.getenv("CI", False),
                                     no_test=(self._facts["test"] and no_test))
        # Try 3 times creating image - error occures with communicating with docker API
        errors = ""
        for trial in range(2):
            try:
                # Building test image
                with tempfile.NamedTemporaryFile(dir=self._pack_abs_dir, suffix=".Dockerfile") as fp:
                    fp.write(dockerfile.encode("utf-8"))
                    fp.seek(0)
                    test_image = self._docker_client.images.build(path=self._pack_abs_dir,
                                                                  dockerfile=os.path.basename(fp.name),
                                                                  tag=docker_base_image[0] + "-test",
                                                                  rm=True)
                    test_image_id = test_image[0].short_id
                break
            except (docker.errors.BuildError, docker.errors.APIError) as e:
                logger.critical(f"{self._pack_name} - build error - {e}")
                if trial == 1:
                    errors = e

        if test_image_id:
            logger.info(f"{self._pack_name} - Image {test_image_id} created succefully")

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
        logger.info(f"{self._pack_name} - Pylint-{test_image} - Start")
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
                logger.error(f"{self._pack_name} - Pylint-{test_image} - Finshed errors found")
                container_log = container_obj.logs().decode("utf-8")
                container_exit_code = 1
            elif container_exit_code in [4, 8, 16]:
                # 4-Warning message issued
                # 8-refactor message issued
                # 16-convention message issued
                logger.warning(f"{self._pack_name} - Pylint-{test_image} - Finshed success - warnings found")
                container_exit_code = 0
            elif container_exit_code == 32:
                # 32-usage error
                logger.critical(f"{self._pack_name} - Pylint-{test_image} - Finished- Usage error")
                return 2, container_log

            # Keeping container if needed or remove it
            if keep_container:
                logger.info(f"{self._pack_name} - Pylint-{test_image} - container name {self._pack_name}-pylint")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{self._pack_name} - Pylint-{test_image} - Unable to delete container - {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{self._pack_name} - Pylint-{test_image} - Unable to run pylint - {e}")
            return 2, container_log

        if container_exit_code:
            logger.error(f"{self._pack_name} - Pylint-{test_image} - Finished errors found")
        else:
            logger.info(f"{self._pack_name} - Pylint-{test_image} - Finished success")

        return container_exit_code, container_log

    def _docker_run_pytest(self, test_image: str, keep_container: bool, test_xml: bool) -> Tuple[int, str]:
        """ Run Pylint in container based to created test image

        Args:
            test_image(str): Test image id/name
            keep_container(bool): True if to keep container after excution finished
            test_xml(str): Xml saving path

        Returns:
            int: 0 on successful, errors 1, neet to retry 2
            str: Unit test json report
        """
        logger.info(f"{self._pack_name} - Pytest-{test_image} - Start")
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
                    xml_apth = os.path.join(test_xml, f'{self._pack_name}_pytest.xml')
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
                logger.critical(f"{self._pack_name} - Pytest-{test_image} - Usage error")
                return 2, test_xml
            # Remove container if not needed
            if keep_container:
                logger.info(f"{self._pack_name} - Pytest-{test_image} - conatiner name {self._pack_name}-pytest")
            else:
                try:
                    container_obj.remove(force=True)
                except docker.errors.NotFound as e:
                    logger.critical(f"{self._pack_name} - Pytest-{test_image} - Unable to remove container {e}")
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            logger.critical(f"{self._pack_name} - Pytest-{test_image} - Unable to run pytest container {e}")
            return 2, test_json

        if container_exit_code:
            logger.error(f"{self._pack_name} - Pytest-{test_image} - Finished errors found")
        else:
            logger.info(f"{self._pack_name} - Pytest-{test_image} - Finished success")

        return container_exit_code, test_json

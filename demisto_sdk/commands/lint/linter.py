# STD python packages
import getpass
import io
import logging
import shutil
import os
from typing import Tuple, Dict, Any, Optional
import requests
import yaml
import tempfile
import mmap
# 3-rd party packages
from docker import DockerClient
from docker import errors as docker_errors
from jinja2 import Environment, FileSystemLoader
# Local packages
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import Errors
from demisto_sdk.commands.common.logger import Colors
from demisto_sdk.commands.common.tools import print_v, get_all_docker_images, get_python_version, \
    print_error, get_yml_paths_in_dir, run_command
from demisto_sdk.commands.lint.commands_builder import *
from demisto_sdk.commands.unify.unifier import Unifier

# Logger object init
logger = logging.getLogger(__name__)


class Linter:
    """Linter used to activate lint command on single package

        Attributes:
            pack_dir: Pack to run lint on.
            req_2: requirements for docker using python2
            req_3: requirements for docker using python3
        """

    def __init__(self, pack_dir: str, req_3: Optional[str], req_2: Optional[str]):
        self.config = Configuration()
        self.req_3 = req_3
        self.req_2 = req_2
        self.pack_abs_dir = os.path.abspath(os.path.join(self.config.env_dir, pack_dir))
        if self.pack_abs_dir[-1] != os.sep:
            self.pack_abs_dir = os.path.join(self.pack_abs_dir, '')
        self.pack_rel_dir = pack_dir
        self.pack_name = self.pack_abs_dir.split("/")[-2]
        self.docker_login_completed = False
        self.common_server_created = False

    def run_dev_packages(self, docker_client: DockerClient, lint_status: Dict[str, Any], pbar, no_flake8: bool,
                         no_bandit: bool,
                         no_mypy: bool, no_pylint: bool, no_test: bool, keep_container: bool) \
            -> Tuple[int, Dict[str, Any], Dict[str, Any]]:
        """Run lint and tests on single package
        Perfroming the follow:
            1. Run the lint on OS - flake8, bandit, mypy.
            2. Run in package docker - pylint, pytest.

        Args:
            docker_client: docker client for communication with docker daemon
            lint_status: all packages lint and test status
            pbar: progress bar object to be updated.
            no_flake8: Whether to skip flake8.
            no_bandit: Whether to skip bandit.
            no_mypy: Whether to skip mypy.
            no_pylint: Whether to skip pylint.
            no_test: Whether to skip pytest.
            keep_container: Whether to keep the test container.

        Returns:
            (exit code 0 if all succeed else 1, lint and test all status, pkg status)
        """
        pkg_lint_status = {
            "pkg": self.pack_name,
            "path": self.pack_rel_dir,
            "images": [],
            "flake8_exit_code": 0,
            "flake8_errors": None,
            "bandit_exit_code": 0,
            "bandit_errors": None,
            "mypy_exit_code": 0,
            "mypy_errors": None,
            "pylint_exit_code": 0,
            "pylint_errors": None,
            "pytest_exit_code": 0,
            "pytest_errors": [],
            "pytest_collected_tests": []
        }

        return_exit_code = 0

        # Loading pkg yaml
        pbar.set_description_str(f"{self.pack_name} - yaml")
        _, yml_path = get_yml_paths_in_dir(self.pack_abs_dir, "")
        if not yml_path:
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Skiping no yaml file found{Colors.Fg.cyan}{yml_path}"
                f"{Colors.reset}")
            return 0, lint_status, pkg_lint_status
        logger.debug(
            f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Using yaml file {Colors.Fg.cyan}{yml_path}"
            f"{Colors.reset}")
        with open(yml_path) as yml_file:
            yml_data = yaml.safe_load(yml_file)
        script_obj = yml_data
        if isinstance(script_obj.get('script'), dict):
            script_obj = script_obj.get('script')
        script_type = script_obj.get('type')
        if script_type != 'python':
            if script_type == 'powershell':
                # TODO powershell linting
                return 0, lint_status, pkg_lint_status
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Skipping due to undefined 'type' in yaml")
            return 0, lint_status, pkg_lint_status
        # Getting docker images from pkg yaml
        images = get_all_docker_images(script_obj)
        logger.debug(
            f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Found images {Colors.Fg.cyan}{','.join(images)}"
            f"{Colors.reset}")
        # Getting python version form docker image
        py_num = get_python_version(images[0], False, True)
        # Copy demisto-mock, CommonServerUserPython to pkg path
        self._setup_dev_files(py_num)
        # Perform lint check on OS
        for lint_check in ["flake8", "bandit", "mypy"]:
            pbar.set_description_str(f"{self.pack_name} - {lint_check}")
            exit_code: int = 0
            output: str = ""
            if lint_check == "flake8":
                if not no_flake8:
                    exit_code, output = self.run_flake8()
            elif lint_check == "bandit":
                if not no_bandit:
                    exit_code, output = self.run_bandit()
            elif lint_check == "mypy":
                if not no_mypy:
                    exit_code, output = self.run_mypy(py_num=py_num)
            if exit_code:
                pkg_lint_status[f"{lint_check}_exit_code"] = exit_code
                pkg_lint_status[f"{lint_check}_errors"] = output
                pkg_lint_status["status"] = 1
                lint_status[f"{lint_check}_exit_code"] = 1
                lint_status[f"{lint_check}_errors"][self.pack_name] = output
                return_exit_code = 1

        # Pylint and pytest excution in pkg docker images
        if not no_test or not no_pylint:
            # Perform pylint and pytest on each declared image
            for image in images:
                # Give each image 2 tries, if first failed willl validate second time
                for try_num in range(1):
                    # gettig py versions
                    py_num = get_python_version(image, False, True)
                    pkg_lint_status["images"].append({"image": image,
                                                      "python_version": py_num})
                    logger.debug(
                        f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Image {Colors.Fg.cyan}{image}{Colors.reset}"
                        f" - python{py_num}")
                    # Setting right pypi requirements file for image
                    if py_num == 2.7:
                        requirements = self.req_2
                    else:
                        requirements = self.req_3
                    # Creating image if pylint specifie or found tests and tests specified
                    pbar.set_description_str(f"{self.pack_name} - create img")
                    docker_image_created = self._docker_image_create(docker_client, image, requirements)
                    # Run pylint and pytest insdie docker
                    need_to_retry = False
                    for check in ["pylint", "pytest"]:
                        exit_code: int = 0
                        output: list = []
                        if not no_test and check == "pytest":
                            pbar.set_description_str(f"{self.pack_name} - pytest")
                            exit_code, output, collected_tests = self._docker_run_pytest(docker_client,
                                                                                         docker_image_created,
                                                                                         keep_container)
                            pkg_lint_status["pytest_collected_tests"] = collected_tests
                        elif not no_pylint and check == "pylint":
                            pbar.set_description_str(f"{self.pack_name} - pylint")
                            exit_code, output = self._docker_run_pylint(docker_client, docker_image_created,
                                                                        keep_container)
                        if exit_code:
                            pkg_lint_status[f"{check}_exit_code"] = exit_code
                            pkg_lint_status[f"{check}_errors"] = output
                            pkg_lint_status["status"] = 1
                            lint_status[f"{check}_errors"][self.pack_name] = output
                            lint_status[f"{check}_exit_code"] = 1
                            return_exit_code = 1
                            need_to_retry = True
                    if not need_to_retry:
                        break

        return return_exit_code, lint_status, pkg_lint_status

    def get_common_server_python(self):
        """Getting common server python in not exists changes self.common_server_created to True if needed.

        Returns:
            bool. True if exists/created, else False
        """
        # If not CommonServerPython is dir
        common_server_target_path = "CommonServerPython.py"
        common_server_remote_path = "https://raw.githubusercontent.com/demisto/content/master/Scripts/" \
                                    "CommonServerPython/CommonServerPython.py"
        if not os.path.isfile(os.path.join(self.pack_abs_dir, common_server_target_path)):
            # Get file from git
            try:
                res = requests.get(common_server_remote_path, verify=False)
                with open(os.path.join(self.pack_abs_dir, common_server_target_path), "w+") as f:
                    f.write(res.text)
                    self.common_server_created = True
            except requests.exceptions.RequestException:
                print_error(Errors.no_common_server_python(common_server_remote_path))
                return False
        return True

    def remove_common_server_python(self):
        """checking if CommonServerPython.py file exists in pack dir and removing it if needed"""
        common_server_target_path = "CommonServerPython.py"
        if self.common_server_created:
            os.remove(os.path.join(self.pack_abs_dir, common_server_target_path))

    def run_flake8(self) -> Tuple[int, str]:
        """Runs flake8 in pack dir

        Returns:
            0 on successful else 1, errors
        """
        logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running flake8")
        lint_files = self._get_lint_file()
        output = run_command(build_flak8_command(lint_files), universal_newlines=False, cwd=self.pack_abs_dir)

        if len(output) == 0:
            logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Flake8 finished - succefully")
            return 0, ""

        logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - flake8 finished - Errors found")
        return 1, output

    def run_mypy(self, py_num: float) -> Tuple[int, str]:
        """Run mypy in pack dir

        Args:
            py_num: The python version in use

        Returns:
           0 on successful else 1, errors
        """
        logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running mypy")
        self.get_common_server_python()
        lint_file = self._get_lint_file()
        # Add typing import if its python2 version - (In old packs using py version 2 does not include this import)
        is_missing = False
        if 2.7 == py_num:
            with open(file=lint_file) as f:
                s = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                if s.find(b"from typing import") == -1 and s.find(b"import typing") == -1:
                    is_missing = True
            if is_missing:
                shutil.copyfile(lint_file, f"{lint_file}_back")
                lint_file = f"{lint_file}_back"

                def line_prepender(filename, line):
                    with open(filename, 'r+') as f:
                        content = f.read()
                        f.seek(0, 0)
                        f.write(line.rstrip('\r\n') + '\n' + content)

                line_prepender(lint_file, line="from typing import *")

        output = run_command(build_mypy_command(lint_file, version=py_num), universal_newlines=False,
                             cwd=self.pack_abs_dir)
        self.remove_common_server_python()
        if is_missing:
            os.remove(lint_file)
        if 'Success: no issues found in 1 source file' in output:
            logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - mypy finished - succefully")
            return 0, ""
        logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - mypy finished - Errors found")
        return 1, output

    def run_bandit(self) -> Tuple[int, str]:
        """Run bandit in pack dir

        Returns:
            0 on successful else 1, errors
        """
        logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running bandit")
        lint_files = self._get_lint_file()
        output = run_command(build_bandit_command(lint_files),
                             universal_newlines=False,
                             cwd=self.pack_abs_dir, )
        if len(output) == 0:
            logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - bandit finished - succefully")
            return 0, ""
        else:
            logging.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - bandit finished - Errors found")
            return 1, output

    def _docker_image_create(self, docker_client: DockerClient, docker_base_image, requirements, ) -> str:
        """Create the docker image:
            1. Installing build base if required in alpine images version - https://wiki.alpinelinux.org/wiki/GCC
            2. Installing pypi packs - if only pylint required - only pylint installed otherwise all pytest and pylint
               installed, packages which being install can be found in path demisto_sdk/commands/lint/dev_envs
            3. The docker image build done by Dockerfile template located in
                demisto_sdk/commands/lint/templates/dockerfile.jinja2

        Args:
            docker_client: docker client object for communicating with docker daemon.
            docker_base_image (string): docker image to use as base for installing dev deps.
            requirements (string): pypi requirements.

        Returns:
            Created test image sha256 shore unique ID
        """
        self.pack_name = self.pack_abs_dir.split("/")[-2]
        logger.debug(
            f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Creating image based on {docker_base_image}")
        # Using DockerFile template
        file_loader = FileSystemLoader(f'{self.config.sdk_env_dir}/lint/templates')
        env = Environment(loader=file_loader, trim_blocks=True, lstrip_blocks=True)
        template = env.get_template('dockerfile.jinja2')
        dockerfile = template.render(image=docker_base_image,
                                     pypi_packs=repr(" " + requirements),
                                     project_dir=self.pack_abs_dir)

        # Building test image
        try:
            with tempfile.NamedTemporaryFile(dir=self.pack_abs_dir, suffix="Dockerfile") as fp:
                fp.write(dockerfile.encode("utf-8"))
                fp.seek(0)
                test_image = docker_client.images.build(path=self.pack_abs_dir,
                                                        dockerfile=os.path.basename(fp.name),
                                                        tag=docker_base_image + "-test",
                                                        forcerm=True)
        except docker_errors.BuildError:
            logger.error(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Failed build test image absed on "
                f"{docker_base_image}")
        except docker_errors.APIError:
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Failed communicating with docker daemon.")

        logger.debug(
            f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Image {docker_base_image} created succefully")
        # Push image to repository if ENV supplied
        if self._docker_login(docker_client):
            logger.info(f"Pushing image: {test_image} to docker hub")
            docker_client.push(test_image)
            logger.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Done creating docker image:"
                         f" {docker_base_image} ")

        return test_image[0].short_id

    def _docker_login(self, docker_client: DockerClient) -> bool:
        """Loging to docker client to dockerhub
        The credentials getting from shell env as vars:
            1. DOCKERHUB_USER - mandatory
            2. DOCKERHUB_PASSWORD - Optional if not filled will prompted to fill.

        Args:
            docker_client: docker client object to communicate with docker daemon

        Returns:
            True if succeed else False
        """
        # Check if allready logged in
        if self.docker_login_completed:
            return True
        # Getting docker login info from enviorment
        docker_user = os.getenv('DOCKERHUB_USER')
        if not docker_user:
            logger.debug('DOCKERHUB_USER not set. Not trying to login to dockerhub')
            return False
        docker_pass = os.getenv('DOCKERHUB_PASSWORD')
        # Get logging password for docker hub if not set
        if docker_pass:
            docker_pass = getpass.getpass()
        # perform login to client
        if docker_pass and docker_user:
            docker_client.login(username=docker_user,
                                password=docker_pass)
            # Test docker hub connection
            login_status = docker_client.ping()
            if not login_status:
                logger.error("Unable to perform login to dockerhub")
                return False

        logger.error("Logged in to dockerhub succefully")
        self.docker_login_completed = True
        return True

    def _docker_run_pylint(self, docker_client: DockerClient, test_image: str, keep_container: bool) -> Tuple[
            int, Optional[list]]:
        """Run Pylint in container based to created test image

        Args:
            docker_client: docker client object to communicate with docker daemon
            test_image: test image id/name
            keep_container: True if to keep container after excution finished

        Returns:
            0 on successful else 1, errors
        """
        logger.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pylint in image {test_image}")
        pylint_files = os.path.basename(self._get_lint_file())
        pylint_command = build_pylint_command(pylint_files)
        # Check if previous run left container a live if it do, we remove it
        try:
            container_obj = docker_client.containers.get(f"{self.pack_name}-pylint")
            container_obj.remove(force=True)
        except docker_errors.NotFound:
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Old {self.pack_name}-pylint isn't exsits -  "
                f"Skipping nothing to delete")

        # Run container
        container_log = None
        try:
            container_obj = docker_client.containers.run(name=f"{self.pack_name}-pylint",
                                                         image=test_image,
                                                         command=[pylint_command],
                                                         detach=True)
            # wait for container to finish
            container_status = container_obj.wait(condition="exited")
            # Get container exit code
            container_exit_code = container_status.get("StatusCode")
            if container_exit_code in [1, 2]:
                # 1-fatal message issued
                # 2-Error message issued
                logger.debug(
                    f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pylint finished - Errors found")
                container_log: list = container_obj.logs().decode("utf-8").split("\n")
                for i in range(len(container_log) - 1):
                    if '********' in container_log[i] or not container_log[i]:
                        container_log.pop(i)
                container_exit_code = 1
            elif container_exit_code in [4, 8, 16]:
                # 4-Warning message issued
                # 8-refactor message issued
                # 16-convention message issued
                logger.debug(
                    f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pylint finished - succefully but"
                    f" found messages lower than error")
                container_exit_code = 0
            elif container_exit_code == 32:
                # 32-usage error
                logger.debug(
                    f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pylint finished - Usage error")
                container_exit_code = "1 (Unable to run pylint - usage error)"

            # Keeping container if needed or remove it
            if keep_container:
                logger.debug(
                    f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pytest finished - conatiner name - "
                    f"{self.pack_name}-pylint - id {container_obj.id}")
            else:
                try:
                    container_obj.remove(force=True)
                except docker_errors.NotFound:
                    logger.debug(
                        f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - {self.pack_name}-pylint -  unable to remove "
                        f"container after finish")
        except docker_errors.ImageNotFound:
            container_exit_code = 1
            container_log = f"Unable to find image {test_image}"
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Old {self.pack_name}-Image not found - container"
                f" running error")
        except docker_errors.APIError:
            container_exit_code = 1
            container_log = f"Failed communicating with docker daemon"
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Failed communicating with docker daemon.")

        return container_exit_code, container_log

    def _docker_run_pytest(self, docker_client: DockerClient, test_image: str, keep_container: bool) -> Tuple[
            int, Optional[list], str]:
        """Run Pylint in container based to created test image

        Args:
            docker_client: docker client object to communicate with docker daemon
            test_image: test image id/name
            keep_container: True if to keep container after excution finished

        Returns:
            0 on successful else 1, errors
        """
        logger.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pytest in image {test_image}")
        pytest_command = build_pytest_command()
        # Check if previous run left container a live if it does, Remove it
        try:
            container_obj = docker_client.containers.get(f"{self.pack_name}-pytest")
            container_obj.remove(force=True)
        except docker_errors.NotFound:
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Old {self.pack_name}-pytest isn't exsits -  Skipping"
                f" nothing to delete")
        try:
            container_obj = docker_client.containers.get(f"{self.pack_name}-pytest-collector")
            container_obj.remove(force=True)
        except docker_errors.NotFound:
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Old {self.pack_name}-pytest isn't exsits -  Skipping"
                f" nothing to delete")
        # Collect tests
        collected_tests = ""
        container_log = []
        try:
            # Running pytest container
            container_obj = docker_client.containers.run(name=f"{self.pack_name}-pytest-collector",
                                                         image=test_image,
                                                         command=["pytest --collect-only -q"],
                                                         detach=True)
            # Waiting for container to be finished
            container_status = container_obj.wait(condition="exited")
            # Getting container exit code
            container_exit_code = container_status.get("StatusCode")
            if container_exit_code == 0:
                collected_tests = container_obj.logs().decode("utf-8")
            elif container_exit_code == 5:
                # No tests were collected
                container_exit_code = 0
            container_obj = docker_client.containers.get(f"{self.pack_name}-pytest-collector")
            container_obj.remove(force=True)
            # Continue if tests found
            if collected_tests:
                # Running pytest container
                container_obj = docker_client.containers.run(name=f"{self.pack_name}-pytest",
                                                             image=test_image,
                                                             command=[pytest_command],
                                                             detach=True)
                # Waiting for container to be finished
                container_status = container_obj.wait(condition="exited")
                # Getting container exit code
                container_exit_code = container_status.get("StatusCode")
                if container_exit_code == 1:
                    # 1-Tests were collected and run but some of the tests failed
                    container_log = container_obj.logs().decode("utf-8").split("\n")
                    start_pointer = 1
                    end_pointer = -2
                    if 'FAILED' not in container_log[start_pointer]:
                        for i in range(2, len(container_log) - 1):
                            if 'FAILED' in container_log[i]:
                                start_pointer = i
                    if 'seconds' not in container_log[-2]:
                        for i in reversed(range(start_pointer, len(container_log) - 1)):
                            if 'seconds' in container_log[i]:
                                end_pointer = i
                    container_log = container_log[start_pointer + 1: end_pointer]
                elif container_exit_code in [2, 3]:
                    # 2-Test execution was interrupted by the user
                    # 3-Internal error happened while executing tests
                    container_exit_code = "1 (Unable to run pytest - execution error)"
                elif container_exit_code == 4:
                    # pytest command line usage error
                    container_exit_code = "1 (Unable to run pytest - usage error)"
                elif container_exit_code == 5:
                    # No tests were collected
                    container_exit_code = 0

                if keep_container:
                    logger.debug(
                        f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pytest finished - conatiner name -"
                        f" {self.pack_name}-pytest")
                else:
                    try:
                        container_obj.remove(force=True)
                    except docker_errors.NotFound:
                        logger.debug(
                            f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - {self.pack_name}-pytest -  unable to "
                            f"remove container after finish")
        except docker_errors.ImageNotFound:
            container_exit_code = f"1 (Unable to run pytest - Unable to find image {test_image})"
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Old {self.pack_name}-Image not found - container"
                f" running error")
        except docker_errors.APIError:
            container_exit_code = f"1 (Unable to run pytest - Failed communicating with docker daemon)"
            logger.debug(
                f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Failed communicating with docker daemon")

        if container_exit_code:
            logger.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pytest finished - Errors found")
        else:
            logger.debug(f"{Colors.Fg.cyan}{self.pack_name}{Colors.reset} - Running pytest finished - succefully")

        return container_exit_code, container_log, collected_tests

    def _setup_dev_files(self, py_num):
        # copy demistomock and common server
        try:
            shutil.copy(self.config.env_dir + '/Tests/demistomock/demistomock.py', self.pack_abs_dir)
            open(self.pack_abs_dir + '/CommonServerUserPython.py', 'a').close()  # create empty file
            shutil.rmtree(self.pack_abs_dir + '/__pycache__', ignore_errors=True)
            shutil.copy(self.config.env_dir + '/Tests/scripts/dev_envs/pytest/conftest.py', self.pack_abs_dir)
            self.check_api_module_imports(py_num)
            if "/Scripts/CommonServerPython" not in self.pack_abs_dir:
                # Otherwise we already have the CommonServerPython.py file
                shutil.copy(self.config.env_dir + '/Scripts/CommonServerPython/CommonServerPython.py',
                            self.pack_abs_dir)
        except Exception as e:
            logger.debug(f'Could not copy demistomock and CommonServer files: {e}')

    def check_api_module_imports(self, py_num):
        """
        Checks if the integration imports an API module and if so pastes the module in the package.
        :param py_num: The python version - api modules are in python 3
        """
        if py_num > 3:
            unifier = Unifier(self.pack_abs_dir)
            code_file_path = unifier.get_code_file('.py')

            try:
                # Look for an import to an API module in the code. If there is such import, we need to copy the correct
                # module file to the package directory.
                with io.open(code_file_path, encoding='utf-8') as script_file:
                    _, module_name = unifier.check_api_module_imports(script_file.read())
                if module_name:
                    module_path = os.path.join(self.config.env_dir, 'Packs', 'ApiModules', 'Scripts',
                                               module_name, module_name + '.py')
                    print_v('Copying ' + os.path.join(self.config.env_dir, 'Scripts', module_path))
                    if not os.path.exists(module_path):
                        raise ValueError('API Module {} not found, you might be outside of the content repository'
                                         ' or this API module does not exist'.format(module_name))
                    shutil.copy(os.path.join(module_path), self.pack_abs_dir)
            except Exception as e:
                print_v('Unable to retrieve the module file {}: {}'.format(module_name, str(e)))

    def _get_lint_file(self) -> str:
        unifier = Unifier(self.pack_abs_dir)
        code_file = unifier.get_code_file('.py')
        return os.path.abspath(code_file)

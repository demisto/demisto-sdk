
import copy
import hashlib
import io
import logging
import os
import shutil
import concurrent.futures
from docker.models.images import Image
import git
import time
import docker
import docker.errors
import docker.models.containers
from contextlib import contextmanager
from shutil import rmtree
from jinja2 import Environment, FileSystemLoader, exceptions
import requests

from ruamel.yaml import YAML
import urllib3
from wcmatch.pathlib import NEGATE, Path
from typing import Any, Dict, List, Optional, Tuple

from demisto_sdk.commands.common.tools import get_all_docker_images
from demisto_sdk.commands.lint.helpers import get_python_version_from_image


logger = logging.getLogger('demisto-sdk')

@contextmanager
def temp_dir(parent_dir: Path, dir_name: str):
    """Create Temp directory for docker context.

     Open:
        - Create temp directory.

    Close:
        - Delete temp directory.
    """
    temp = parent_dir / dir_name
    try:
        temp.mkdir(parents=True, exist_ok=True)
        yield temp
    finally:
        rmtree(temp)

class DockersManager:

    def __init__(self, content_repo: Path, pkgs: List[Path], modules: dict, docker_timeout: int, req_3: list, req_2: list) -> None:
        self._content_repo = content_repo
        self._images_data: Dict = {}
        self._image_to_test_image_map: Dict = {}
        self._pkgs = pkgs
        self._modules = modules
        # self._docker_client: docker.DockerClient = docker.from_env(timeout=docker_timeout)
        # self._docker_hub_login = self._docker_login()
        self._req_3 = req_3
        self._req_2 = req_2

    def prepare_required_images(self):

        self.collect_lint_files_and_py_version()
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for image_name, image_files_and_v in self._images_data.items(): 
                py_version = image_files_and_v[0]
                lint_files = image_files_and_v[1]
                results.append(executor.submit(self._docker_image_create, [image_name, py_version], lint_files))                    
            
            for future in concurrent.futures.as_completed(results):
                image_name, test_image, errors = future.result()
                if not errors:
                    self._image_to_test_image_map[image_name] = test_image
                    
        
    def _docker_image_create(self, docker_base_image: List[Any], lint_files: List[Path]) -> Tuple[str, str]:
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
        docker_client: docker.DockerClient = docker.from_env(timeout=60)
        image_name = docker_base_image[0]
        temp_dir_name = f'temp_lint_data_{hashlib.md5(image_name.encode("utf-8")).hexdigest()}'
        with temp_dir(self._content_repo, temp_dir_name): 
            log_prompt = ''
            test_image_id = ""
            # Get requirements file for image
            requirements = []
            if 2 < docker_base_image[1] < 3:
                requirements = self._req_2
            elif docker_base_image[1] >= 3:
                requirements = self._req_3
            
            docker_context_dir = self._content_repo/temp_dir_name
            for lint_file in lint_files:
                shutil.copy(src=lint_file, dst=docker_context_dir)
            # Using DockerFile template
            file_loader = FileSystemLoader(Path(__file__).parent / 'templates')
            env = Environment(loader=file_loader, lstrip_blocks=True, trim_blocks=True, autoescape=True)
            template = env.get_template('dockerfile.jinja2')
            try:
                dockerfile = template.render(image=docker_base_image[0],
                                            pypi_packs=requirements,
                                            pack_type='python',
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
                test_image = docker_client.images.pull(test_image_name)
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
                        docker_client.images.build(fileobj=f,
                                                        tag=test_image_name,
                                                        forcerm=True)

                        if self._docker_login(docker_client=docker_client):
                            for trial in range(2):
                                try:
                                    docker_client.images.push(test_image_name)
                                    logger.info(f"{log_prompt} - Image {test_image_name} pushed to repository")
                                    break
                                except (requests.exceptions.ConnectionError, urllib3.exceptions.ReadTimeoutError,
                                        requests.exceptions.ReadTimeout):
                                    logger.info(f"{log_prompt} - Unable to push image {test_image_name} to repository")

                except (docker.errors.BuildError, docker.errors.APIError, Exception) as e:
                    logger.critical(f"{log_prompt} - Build errors occurred {e}")
                    errors = str(e)
            else:
                logger.info(f"{log_prompt} - Found existing image {test_image_name}")
            dockerfile_path = docker_context_dir / ".Dockerfile"
            dockerfile = template.render(image=test_image_name,
                                        copy_pack=True)
            with open(dockerfile_path, mode="w+") as file:
                file.write(str(dockerfile))
            # we only do retries in CI env where docker build is sometimes flacky
            build_tries = int(os.getenv('DEMISTO_SDK_DOCKER_BUILD_TRIES', 3)) if os.getenv('CI') else 1
            for trial in range(build_tries):
                try:
                    logger.info(f"{log_prompt} - Copy pack dir to image {test_image_name}")
                    build_image_start = time.time()
                    docker_image_final = docker_client.images.build(path=str(dockerfile_path.parent),
                                                                        dockerfile=dockerfile_path.stem,
                                                                        forcerm=True)
                    logger.info(f'Build image test files take: {time.time() - build_image_start}s')
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

            return image_name, test_image_name, errors

    def get_test_image_for_base_image(self, base_image: str):
        return self._image_to_test_image_map.get(base_image)

    def collect_lint_files_and_py_version(self):
        """
        """
        
        for pack_path in sorted(self._pkgs):
            yml_file: Optional[Path] = pack_path.glob([r'*.yaml', r'*.yml', r'!*unified*.yml'], flags=NEGATE)

            if not yml_file:
                logger.info(f"{pack_path} - Skipping no yaml file found {yml_file}")
                continue
            else:
                try:
                    yml_file = next(yml_file)
                except StopIteration:
                    return True
            
            # Parsing pack yaml - in order to get the dockr images
            try:
                script_obj: Dict = {}
                yml_obj: Dict = YAML().load(yml_file)
                if isinstance(yml_obj, dict):
                    script_obj = yml_obj.get('script', {}) if isinstance(yml_obj.get('script'), dict) else yml_obj
                    py_version = 3 if (script_obj.get('subtype', 'python3') == 'python3') else 2.7


                images = [[image, -1] for image in get_all_docker_images(script_obj=script_obj)]
                if images:
                    lint_files = self.get_all_lint_files(pack_path=pack_path)

                    image_data = self._images_data.get(images[0][0])
                    if not image_data:
                        image_lint_files = []
                        # py_version = get_python_version_from_image(images[0][0], docker_client=self._docker_client)
                        self._images_data[images[0][0]] = (py_version, image_lint_files)
                    image_lint_files.extend(lint_files)
            except (FileNotFoundError, IOError, KeyError):
                logger.info(f'Unable to parse package yml {yml_file}')

    def get_lint_files_for_image(self, image_name: str):

        if not self._lint_files_per_image:
            self.prepare_lint_files_per_images()
        
        return  self._lint_files_per_image.get(image_name)
        
    def get_all_lint_files(self, pack_path: Path):


        lint_files = set(pack_path.glob(["*.py", "!__init__.py", "!*.tmp"], flags=NEGATE))

        # # Facts for Powershell pack
        #     # Get lint files
        #     lint_files = set(
        #         self._pack_abs_dir.glob(["*.ps1", "!*Tests.ps1", "CommonServerPowerShell.ps1", "demistomock.ps1'"],
        #                                 flags=NEGATE))

        # Add CommonServer to the lint checks
        if 'commonserver' in pack_path.name.lower():
            pass
            # # Powershell
            # if self._pkg_lint_status["pack_type"] == TYPE_PWSH:
            #     self._facts["lint_files"] = [Path(self._pack_abs_dir / 'CommonServerPowerShell.ps1')]
            # # Python
            # elif self._pkg_lint_status["pack_type"] == TYPE_PYTHON:
            #     self._facts["lint_files"] = [Path(self._pack_abs_dir / 'CommonServerPython.py')]
        else:
            test_modules = {pack_path / module.name for module in self._modules.keys()}
            lint_files = lint_files.difference(test_modules)
            lint_files = list(lint_files)

        # Remove files that are in gitignore
        log_prompt = ''
        if lint_files:
            self._split_lint_files(lint_files)
            lint_files = self._remove_gitignore_files(lint_files, log_prompt)
            for lint_file in lint_files:
                logger.info(f"{log_prompt} - Lint file {lint_file}")
        else:
            logger.info(f"{log_prompt} - Lint files not found")

        return lint_files

    def _remove_gitignore_files(self, lint_files: List, log_prompt: str) -> None:
        """
        Skipping files that matches gitignore patterns.
        Args:
            log_prompt(str): log prompt string

        Returns:

        """
        try:
            repo = git.Repo(self._content_repo)
            files_to_ignore = repo.ignored(lint_files)
            for file in files_to_ignore:
                logger.info(f"{log_prompt} - Skipping gitignore file {file}")

            return [path for path in lint_files if str(path) not in files_to_ignore]

        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            logger.debug("No gitignore files is available")

    def _split_lint_files(self, lint_files: List):
        """ Remove unit test files from lint_files 
        This is because not all lints should be done on unittest files.
        """
        lint_files_list = copy.deepcopy(lint_files)
        for lint_file in lint_files_list:
            if lint_file.name.startswith('test_') or lint_file.name.endswith('_test.py'):
                lint_files.remove(lint_file)

    def _docker_login(self, docker_client) -> bool:
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
            docker_client.login(username=docker_user,
                                      password=docker_pass,
                                      registry="https://index.docker.io/v1")
            return docker_client.ping()
        except docker.errors.APIError:
            return False
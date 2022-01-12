
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
from typing import Any, Dict, List, Optional, Set, Tuple
from demisto_sdk.commands.common.constants import TYPE_PYTHON

from demisto_sdk.commands.common.tools import get_all_docker_images
from demisto_sdk.commands.lint.helpers import add_tmp_lint_files, get_python_version_from_image, is_lint_available_for_pack_type
from demisto_sdk.commands.lint.mandatory_files_manager import LintFilesInfoHelper


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

    def __init__(self, content_repo: Path, pkgs: List[Path], lint_files_helper: LintFilesInfoHelper, docker_timeout: int, req_3: list, req_2: list) -> None:
        self._content_repo = content_repo
        self._images_data: Dict = {}
        self._image_to_test_image_map: Dict = {}
        self._pkgs = pkgs
        self._lint_files_helper = lint_files_helper
        self._docker_client: docker.DockerClient = docker.from_env(timeout=docker_timeout)
        self._docker_hub_login = self._docker_login(self._docker_client)
        self._req_3 = req_3
        self._req_2 = req_2
        self._images_facts = {}

    def build_required_images(self):
        
        start_time = time.time()
        try:
            self.gather_images_facts()
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                for image_name, image_fact in self._images_facts.items(): 
                    results.append(executor.submit(self._docker_image_create, image_name, image_fact))                    
                
                for future in concurrent.futures.as_completed(results):
                    image_name, test_image, errors = future.result()
                    if not errors:
                        self._image_to_test_image_map[image_name] = test_image
        finally:
            logger.info(f'Build required images take: {time.time() - start_time}s')
        

    #  def _add_mandatory_modules(self):

    #      for pack_path in self._pkgs:
    #         add_tmp_lint_files(self._content_repo, pack_path=pack_path, )      
        
    def _docker_image_create(self, image_name: str, image_fact: Dict) -> Tuple[str, str]:
        """ Create docker image:
            1. Installing 'build base' if required in alpine images version - https://wiki.alpinelinux.org/wiki/GCC
            2. Installing pypi packs - if only pylint required - only pylint installed otherwise all pytest and pylint
               installed, packages which being install can be found in path demisto_sdk/commands/lint/dev_envs
            3. The docker image build done by Dockerfile template located in
                demisto_sdk/commands/lint/templates/dockerfile.jinja2

        Args:
            image_name(str): the docker image to use as base, python version, pack type

        Returns:
            str, str. image name to use and errors string.
        """
        docker_client: docker.DockerClient = docker.from_env(timeout=60)
        temp_dir_name = f'temp_lint_data_{hashlib.md5(image_name.encode("utf-8")).hexdigest()}'
        py_version = image_fact['py_version']
        pakcs_type = image_fact['packs_type']
        with temp_dir(self._content_repo, temp_dir_name): 
            log_prompt = ''
            test_image_id = ""
            # Get requirements file for image
            requirements = []
            if 2 < py_version < 3:
                requirements = self._req_2
            elif py_version > 3:
                requirements = self._req_3
            
            docker_context_dir = self._content_repo/temp_dir_name
            for file in image_fact['image_files']:
                if file.exists():
                    shutil.copy(src=file, dst=docker_context_dir)
                else:
                    logger.info(f'File not found: {str(file)}')
            # Using DockerFile template
            file_loader = FileSystemLoader(Path(__file__).parent / 'templates')
            env = Environment(loader=file_loader, lstrip_blocks=True, trim_blocks=True, autoescape=True)
            template = env.get_template('dockerfile.jinja2')
            try:
                dockerfile = template.render(image=image_name,
                                            pypi_packs=requirements,
                                            pack_type=pakcs_type,
                                            copy_pack=False)
            except exceptions.TemplateError as e:
                logger.debug(f"{log_prompt} - Error when build image - {e.message()}")
                return test_image_id, str(e)
            # Trying to pull image based on dockerfile hash, will check if something changed
            errors = ""
            test_image_name = f'devtest{image_name}-{hashlib.md5(dockerfile.encode("utf-8")).hexdigest()}'
            test_image = None
            try:
                logger.info(f"{log_prompt} - Trying to pull existing image {test_image_name}")
                test_image = docker_client.images.pull(test_image_name)
            except (docker.errors.APIError, docker.errors.ImageNotFound):
                logger.info(f"{log_prompt} - Unable to find image {test_image_name}")
            # Creatng new image if existing image isn't found
            if not test_image:
                logger.info(
                    f"{log_prompt} - Creating image based on {image_name} - Could take 2-3 minutes at first "
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

    def gather_images_facts(self):
        """
        """
        start_time = time.time()
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                for pack_path in sorted(self._pkgs):
                    futures.append(executor.submit(self.gather_single_iamge_facts, pack_path)) 
                
                for future in concurrent.futures.as_completed(futures):
                    image_name, image_facts = future.result()
                    if image_name and image_facts:
                        cached_image_facts = self._images_facts.get(image_name)
                        if cached_image_facts is None:
                            self._images_facts[image_name] = cached_image_facts = image_facts
                        
                        image_failes = image_facts.get('image_files', set())
                        cached_image_facts.get('image_files', set()).update(image_failes)
        
        logger.info(f'Collecting images facts take: {time.time() - start_time}s')

    def gather_single_iamge_facts(self, pack_path: Path) -> Tuple[str, dict]:

        log_prompt = f'Pack {pack_path.name} collect docker image facts'
        script_obj: Dict = self._get_script_obj_from_pack_yml(pack_path=pack_path)
        if script_obj:
            pack_type = script_obj.get('type', TYPE_PYTHON)
            if not is_lint_available_for_pack_type(pack_type):
                logger.info(f'{log_prompt} - Skipping due to not Python, Powershell package - Pack is {pack_type}')
                return None, None
            
            images = [image for image in get_all_docker_images(script_obj=script_obj)]
            if images:
                image_name = images[-1]
                image_facts = {}
                image_facts['py_version'] = get_python_version_from_image(image=image_name, docker_client=self._docker_client)
                image_facts['packs_type'] = pack_type
                image_facts['image_files'] = self._get_files_to_copy_to_image(pack_path, pack_type)
                return image_name, image_facts
            else:
                logger.info(f'{log_prompt} - Skipping due to not images was found')
        else:
            logger.info(f'{log_prompt} - Skipping due to not script object was found')

    def _get_files_to_copy_to_image(self, pack_path: Path, pack_type: str) -> Set:
        lint_files = self._lint_files_helper.get_lint_files_for_pack(pack_path=pack_path, pack_type=pack_type)
        mandatory_files = self._lint_files_helper.get_mandatory_files_for_pack(pack_path=pack_path, pack_type=pack_type)
        return lint_files and mandatory_files and lint_files | mandatory_files 

    def _get_script_obj_from_pack_yml(self, pack_path: Path):
        
        yml_file: Optional[Path] = pack_path.glob([r'*.yaml', r'*.yml', r'!*unified*.yml'], flags=NEGATE)

        if not yml_file:
            logger.info(f"{pack_path.name} - Skipping no yaml file found in {pack_path}")
            return None
        else:
            try:
                yml_file = next(yml_file)
            except StopIteration:
                return None
        
        # Parsing pack yaml - in order to get the dockr images
        try:
            yml_obj: Dict = YAML().load(yml_file)
            if isinstance(yml_obj, dict):
                return yml_obj.get('script', {}) if isinstance(yml_obj.get('script'), dict) else yml_obj
        except (FileNotFoundError, IOError, KeyError):
            logger.info(f'Unable to parse package yml {yml_file}')

    def get_lint_files_for_image(self, image_name: str):

        if not self._lint_files_per_image:
            self.prepare_lint_files_per_images()
        
        return  self._lint_files_per_image.get(image_name)
        
    def get_lint_files(self, pack_path: Path):


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
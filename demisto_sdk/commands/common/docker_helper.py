import functools
import hashlib
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import docker
import requests
import urllib3
from docker.types import Mount
from packaging.version import Version
from requests import JSONDecodeError
from requests.exceptions import RequestException

from demisto_sdk.commands.common.constants import (
    DEFAULT_DOCKER_REGISTRY_URL,
    DEFAULT_PYTHON2_VERSION,
    DEFAULT_PYTHON_VERSION,
    DOCKER_REGISTRY_URL,
    DOCKERFILES_INFO_REPO,
    TYPE_PWSH,
    TYPE_PYTHON,
    TYPE_PYTHON2,
    TYPE_PYTHON3,
)
from demisto_sdk.commands.common.docker_images_metadata import DockerImagesMetadata
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry

DOCKER_CLIENT = None
FILES_SRC_TARGET = List[Tuple[os.PathLike, str]]
# this will be used to determine if the system supports mounts
CAN_MOUNT_FILES = bool(os.getenv("CONTENT_GITLAB_CI", False)) or (
    (not os.getenv("CIRCLECI", False))
    and (
        (not os.getenv("DOCKER_HOST"))
        or os.getenv("DOCKER_HOST", "").lower().startswith("unix:")
    )
)

DEMISTO_PYTHON_BASE_IMAGE_REGEX = re.compile(
    r"[\d\w]+/python3?:(?P<python_version>[23]\.\d+(\.\d+)?)"
)

TEST_REQUIREMENTS_DIR = Path(__file__).parent.parent / "lint" / "resources"


class DockerException(Exception):
    pass


def init_global_docker_client(timeout: int = 60, log_prompt: str = ""):
    global DOCKER_CLIENT
    if DOCKER_CLIENT is None:
        if log_prompt:
            logger.debug(f"{log_prompt} - init and login the docker client")
        else:
            logger.debug("init and login the docker client")
        if ssh_client := os.getenv("DOCKER_SSH_CLIENT") is not None:
            logger.debug(f"{log_prompt} - Using ssh client setting: {ssh_client}")
        logger.debug(f"{log_prompt} - Using docker mounting: {CAN_MOUNT_FILES}")
        try:
            DOCKER_CLIENT = docker.from_env(timeout=timeout, use_ssh_client=ssh_client)  # type: ignore
        except docker.errors.DockerException:
            logger.warning(
                f"{log_prompt} - Failed to init docker client. "
                "This might indicate that your docker daemon is not running."
            )
            raise
        docker_user = os.getenv("DEMISTO_SDK_CR_USER", os.getenv("DOCKERHUB_USER"))
        docker_pass = os.getenv(
            "DEMISTO_SDK_CR_PASSWORD", os.getenv("DOCKERHUB_PASSWORD")
        )
        if docker_user and docker_pass:
            logger.debug(f"{log_prompt} - logging in to docker registry")
            try:
                docker_login(DOCKER_CLIENT)
            except Exception:
                logger.exception(f"{log_prompt} - failed to login to docker registry")
    else:
        msg = "docker client already available, using current DOCKER_CLIENT"
        logger.debug(f"{log_prompt} - {msg}" if log_prompt else msg)
    return DOCKER_CLIENT


def is_custom_registry():
    return (
        not os.getenv("CONTENT_GITLAB_CI")
        and DOCKER_REGISTRY_URL != DEFAULT_DOCKER_REGISTRY_URL
    )


@functools.lru_cache
def docker_login(docker_client) -> bool:
    """Login to docker-hub using environment variables:
            1. DOCKERHUB_USER - User for docker hub.
            2. DOCKERHUB_PASSWORD - Password for docker-hub.
        Used in Circle-CI for pushing into repo devtestdemisto

    Returns:
        bool: True if logged in successfully.
    """
    docker_user = os.getenv("DEMISTO_SDK_CR_USER", os.getenv("DOCKERHUB_USER"))
    docker_pass = os.getenv("DEMISTO_SDK_CR_PASSWORD", os.getenv("DOCKERHUB_PASSWORD"))
    if docker_user and docker_pass:
        try:
            if not is_custom_registry():

                docker_client.login(
                    username=docker_user,
                    password=docker_pass,
                    registry="https://index.docker.io/v1",
                )
                ping = docker_client.ping()
                logger.debug(f"Successfully connected to dockerhub, login {ping=}")
                return ping
            else:
                # login to custom docker registry
                docker_client.login(
                    username=docker_user,
                    password=docker_pass,
                    registry=DOCKER_REGISTRY_URL,
                )
                ping = docker_client.ping()
                logger.debug(
                    f"Successfully connected to {DOCKER_REGISTRY_URL}, login {ping=}"
                )
                return ping
        except docker.errors.APIError:
            logger.info(f"Did not successfully log in to {DOCKER_REGISTRY_URL}")
            return False

    logger.debug(f"Did not log in to {DOCKER_REGISTRY_URL}")
    return False


@functools.lru_cache
def get_pip_requirements_from_file(requirements_file: Path) -> List[str]:
    """
    Get the pip requirements from a requirements file.
    Args:
        requirements_file: The path to the requirements file.

    Returns:
        A list of pip requirements.
    """
    return requirements_file.read_text().strip().splitlines()


class DockerBase:
    def __init__(self):
        self.tmp_dir_name = tempfile.TemporaryDirectory(
            prefix=os.path.join(os.getcwd(), "tmp")
        )
        self.tmp_dir = Path(self.tmp_dir_name.name)
        installation_scripts = (
            Path(__file__).parent.parent / "lint" / "resources" / "installation_scripts"
        )
        self.installation_scripts = {
            TYPE_PYTHON: installation_scripts / "python_image.sh",
            TYPE_PYTHON2: installation_scripts / "python_image.sh",
            TYPE_PYTHON3: installation_scripts / "python_image.sh",
            TYPE_PWSH: installation_scripts / "powershell_image.sh",
        }
        self.changes = {
            TYPE_PWSH: ["WORKDIR /devwork"],
            TYPE_PYTHON: ["WORKDIR /devwork", 'ENTRYPOINT ["/bin/sh", "-c"]'],
            TYPE_PYTHON2: ["WORKDIR /devwork", 'ENTRYPOINT ["/bin/sh", "-c"]'],
            TYPE_PYTHON3: ["WORKDIR /devwork", 'ENTRYPOINT ["/bin/sh", "-c"]'],
        }
        self.requirements = self.tmp_dir / "requirements.txt"
        self.requirements.touch()
        self._files_to_push_on_installation: FILES_SRC_TARGET = [
            (self.requirements, "/test-requirements.txt"),
        ]

    def __del__(self):
        del self.tmp_dir_name

    def installation_files(self, container_type: str) -> FILES_SRC_TARGET:
        files = self._files_to_push_on_installation.copy()
        files.append((self.installation_scripts[container_type], "/install.sh"))
        return files

    @staticmethod
    def pull_image(image: str) -> docker.models.images.Image:
        """
        Get a local docker image, or pull it when unavailable.
        """
        docker_client = init_global_docker_client(log_prompt="pull_image")
        try:
            return docker_client.images.get(image)

        except docker.errors.ImageNotFound:
            logger.debug(f"docker {image=} not found locally, pulling")
            ret = docker_client.images.pull(image)
            logger.debug(f"pulled docker {image=} successfully")
            return ret

    @staticmethod
    def is_image_available(
        image: str,
    ) -> bool:
        docker_client = init_global_docker_client(log_prompt="get_image")
        try:
            docker_client.images.get(image)
            return True
        except docker.errors.ImageNotFound as e:
            if ":" not in image:
                repo = image
                tag = "latest"
            elif image.count(":") > 1:
                raise ValueError(f"Invalid docker image: {image}") from e
            else:
                try:
                    repo, tag = image.split(":")
                    token = _get_docker_hub_token(repo)
                    if _get_image_digest(repo, tag, token):
                        return True
                except RuntimeError as e:
                    logger.debug(f"Error getting image data {image}: {e}")
                    return False
        return False

    @staticmethod
    def copy_files_container(
        container: docker.models.containers.Container, files: FILES_SRC_TARGET
    ):
        """
        Args:
            container: the container object.
            files: a list of (target path in container, source path in machine).
        """
        if files:
            with tempfile.NamedTemporaryFile() as tar_file_path:
                with tarfile.open(name=tar_file_path.name, mode="w") as tar_file:
                    for src, dst in files:
                        try:
                            tar_file.add(src, arcname=dst)
                        except Exception as error:
                            logger.debug(error)
                with open(tar_file_path.name, "rb") as byte_file:
                    container.put_archive("/", byte_file.read())

    @retry(
        times=3,
        exceptions=(
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            DockerException,
        ),
    )
    def create_container(
        self,
        image: str,
        command: Union[str, List[str], None] = None,
        files_to_push: Optional[FILES_SRC_TARGET] = None,
        environment: Optional[Dict] = None,
        **kwargs,
    ) -> docker.models.containers.Container:
        """
        Creates a container and pushing requested files to the container.
        """
        docker_client = init_global_docker_client()

        try:
            container: docker.models.containers.Container = (
                docker_client.containers.create(
                    image=image, command=command, environment=environment, **kwargs
                )
            )
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            DockerException,
        ) as e:
            if container_name := kwargs.get("name"):
                if container := docker_client.containers.get(
                    container_id=container_name
                ):
                    container.remove(force=True)
            raise e

        if files_to_push:
            self.copy_files_container(container, files_to_push)

        return container

    def push_image(self, image: str, log_prompt: str = ""):
        """This pushes the test image to dockerhub if the DOCKERHUB env variables are set

        Args:
            image (str): The image to push
            log_prompt (str, optional): The log prompt to print. Defaults to "".
        """
        for _ in range(2):
            try:

                test_image_name_to_push = image.replace(f"{DOCKER_REGISTRY_URL}/", "")
                docker_push_output = init_global_docker_client().images.push(
                    test_image_name_to_push
                )
                logger.info(
                    f"{log_prompt} - Trying to push Image {test_image_name_to_push} to repository. Output = {docker_push_output}"
                )
                break
            except (
                requests.exceptions.ConnectionError,
                urllib3.exceptions.ReadTimeoutError,
                requests.exceptions.ReadTimeout,
            ):
                logger.warning(
                    f"{log_prompt} - Unable to push image {image} to repository",
                    exc_info=True,
                )

    def create_image(
        self,
        base_image: str,
        image: str,
        container_type: str = TYPE_PYTHON,
        install_packages: Optional[List[str]] = None,
        push: bool = False,
        log_prompt: str = "",
    ) -> docker.models.images.Image:
        """
        this function is used to create a new image of devtestsdemisto docker images.
        Args:
            base_image(str): the base docker image e.g. demisto/python3:3.10.0.23456
            image(str) the new image name to create e.g. devtestsdemisto/python3:3.10.0.23456-d41d8cd98f00b204e9800998ecf8427e
            container_type(str): can be 'python' or 'powershell'
            install_packages(list(str)): pip packages to install e.g ["pip='*'", "pytlint==1.2.3"]
        Returns:
            the new created image
        Flow:
            1. creating a container using an existing image
            2. running the istallation scripts
            3. committing the docker changes (installed packages) to a new local image
        """
        self.requirements.write_text(
            "\n".join(install_packages) if install_packages else ""
        )
        logger.debug(f"Trying to pull image {base_image}")
        self.pull_image(base_image)
        container = self.create_container(
            image=base_image,
            files_to_push=self.installation_files(container_type),
            command="/install.sh",
        )
        container.start()
        if container.wait().get("StatusCode") != 0:
            container_logs = container.logs()
            raise docker.errors.BuildError(
                reason=f"Installation script failed to run on container '{container.id}', {container_logs=}",
                build_log=container_logs,
            )
        repository, tag = image.split(":")
        container.commit(
            repository=repository, tag=tag, changes=self.changes[container_type]
        )
        if os.getenv("CONTENT_GITLAB_CI"):
            container.commit(
                repository=repository.replace(f"{DOCKER_REGISTRY_URL}/", ""),
                tag=tag,
                changes=self.changes[container_type],
            )
        if push and os.getenv("CONTENT_GITLAB_CI"):
            self.push_image(image, log_prompt=log_prompt)
        return image

    @staticmethod
    def get_image_registry(image: str) -> str:
        if DOCKER_REGISTRY_URL not in image:
            return f"{DOCKER_REGISTRY_URL}/{image}"
        return image

    def get_or_create_test_image(
        self,
        base_image: str,
        container_type: str = TYPE_PYTHON,
        python_version: Optional[int] = None,
        additional_requirements: Optional[List[str]] = None,
        push: bool = False,
        should_pull: bool = True,
        log_prompt: str = "",
    ) -> Tuple[str, str]:
        """This will generate the test image for the given base image.

        Args:
            base_image (str): The base image to create the test image
            container_type (str, optional): The container type (powershell or python). Defaults to TYPE_PYTHON.

        Returns:
            The test image name and errors to create it if any
        """

        errors = ""
        if (
            not python_version
            and container_type != TYPE_PWSH
            and (version := get_python_version(base_image))
        ):
            python_version = version.major
        python3_requirements = get_pip_requirements_from_file(
            TEST_REQUIREMENTS_DIR / "python3_requirements" / "dev-requirements.txt"
        )
        python2_requirements = get_pip_requirements_from_file(
            TEST_REQUIREMENTS_DIR / "python2_requirements" / "dev-requirements.txt"
        )
        pip_requirements = []
        if python_version:
            pip_requirements = {3: python3_requirements, 2: python2_requirements}.get(
                python_version, []
            )

        if additional_requirements:
            pip_requirements.extend(additional_requirements)
        identifier = hashlib.md5(
            "\n".join(sorted(pip_requirements)).encode("utf-8")
        ).hexdigest()

        test_docker_image = (
            f'{base_image.replace("demisto", "devtestdemisto")}-{identifier}'
        )
        if is_custom_registry():
            # if we use a custom registry, we need to have to pull the image and we can't use dockerhub api
            should_pull = True
        if not should_pull and self.is_image_available(test_docker_image):
            return test_docker_image, errors
        base_image = self.get_image_registry(base_image)
        test_docker_image = self.get_image_registry(test_docker_image)

        try:
            logger.debug(
                f"{log_prompt} - Trying to pull existing image {test_docker_image}"
            )
            self.pull_image(test_docker_image)
        except (docker.errors.APIError, docker.errors.ImageNotFound):
            logger.info(
                f"{log_prompt} - Unable to find image {test_docker_image}. Creating image based on {base_image} - Could take 2-3 minutes at first"
            )
            try:
                self.create_image(
                    base_image,
                    test_docker_image,
                    container_type,
                    pip_requirements,
                    push=push,
                )
            except (docker.errors.BuildError, docker.errors.APIError, Exception) as e:
                errors = str(e)
                logger.critical(f"{log_prompt} - Build errors occurred: {errors}")
        return test_docker_image, errors


class MountableDocker(DockerBase):
    def __init__(self):
        super().__init__()
        files = [
            Path("/etc/ssl/certs/ca-certificates.crt"),
            Path("/etc/pip.conf"),
        ]
        for file in files:
            if file.exists():
                self._files_to_push_on_installation.append(
                    (shutil.copyfile(file, self.tmp_dir / file.name), str(file))
                )

    @staticmethod
    def get_mounts(files: FILES_SRC_TARGET) -> List[Mount]:
        """
        Args:
            files: a list of (target path in container, source path in machine).
        Returns:
            a list of mounts
        """
        mounts = []
        for src, target in files:
            try:
                src = Path(src)
                if src.exists():
                    mounts.append(Mount(target, str(src.absolute()), "bind"))
            except Exception:
                logger.debug(f"Failed to mount {src} to {target}")
        return mounts

    def create_container(
        self,
        image: str,
        command: Union[str, List[str], None] = None,
        files_to_push: Optional[FILES_SRC_TARGET] = None,
        environment: Optional[Dict] = None,
        mount_files: bool = CAN_MOUNT_FILES,
        **kwargs,
    ) -> docker.models.containers.Container:
        """
        Creates a container and pushing requested files to the container.
        """
        kwargs = kwargs or {}
        if files_to_push and mount_files:
            return super().create_container(
                image=image,
                command=command,
                environment=environment,
                mounts=self.get_mounts(files_to_push),
                files_to_push=None,
                **kwargs,
            )
        else:
            return super().create_container(
                image=image,
                command=command,
                environment=environment,
                files_to_push=files_to_push,
                **kwargs,
            )


def get_docker():
    return MountableDocker() if CAN_MOUNT_FILES else DockerBase()


def _get_python_version_from_tag_by_regex(image: str) -> Optional[Version]:
    if match := DEMISTO_PYTHON_BASE_IMAGE_REGEX.match(image):
        return Version(match.group("python_version"))

    return None


@retry(times=5, exceptions=(RuntimeError, RequestException))
def _get_docker_hub_token(repo: str) -> str:
    auth = None

    # If the user has credentials for docker hub, use them to get the token
    if (docker_user := os.getenv("DOCKERHUB_USER")) and (
        docker_pass := os.getenv("DOCKERHUB_PASSWORD")
    ):
        logger.debug("Using docker hub credentials to get token")
        auth = (docker_user, docker_pass)

    response = requests.get(
        f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull",
        auth=auth,
    )
    if not response.ok:
        raise RuntimeError(f"Failed to get docker hub token: {response.text}")
    try:
        return response.json()["token"]
    except (JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Failed to get docker hub token: {response.text}") from e


def _get_image_digest(repo: str, tag: str, token: str) -> str:
    response = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
        headers={
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
            "Authorization": f"Bearer {token}",
        },
    )
    if not response.ok:
        raise RuntimeError(f"Failed to get docker image digest: {response.text}")
    try:
        return response.json()["config"]["digest"]
    except (JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Failed to get docker image digest: {response.text}") from e


@functools.lru_cache
def _get_image_env(repo: str, digest: str, token: str) -> List[str]:
    response = requests.get(
        f"https://registry-1.docker.io/v2/{repo}/blobs/{digest}",
        headers={
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
            "Authorization": f"Bearer {token}",
        },
    )
    if not response.ok:
        raise RuntimeError(f"Failed to get docker image env: {response.text}")
    try:
        return response.json()["config"]["Env"]
    except (JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Failed to get docker image env: {response.text}") from e


def _get_python_version_from_env(env: List[str]) -> Version:
    python_version_envs = tuple(
        filter(lambda env: env.startswith("PYTHON_VERSION="), env)
    )
    return (
        Version(python_version_envs[0].split("=")[1])
        if python_version_envs
        else Version(DEFAULT_PYTHON_VERSION)
    )


@functools.lru_cache
def get_python_version(image: Optional[str]) -> Optional[Version]:
    """
    Get the python version of a docker image if exist.

    Args:
        image (str): the docker image

    Returns:
        Version: Python version X.Y (3.7, 3.6, ..)
    """
    logger.debug(f"Get python version from image {image=}")

    if not image:
        # When no docker_image is specified, we use the default python version which is Python 2.7.18
        logger.debug(
            f"No docker image specified or a powershell image, using default python version: {DEFAULT_PYTHON2_VERSION}"
        )
        return Version(DEFAULT_PYTHON2_VERSION)

    if "pwsh" in image or "powershell" in image:
        logger.debug(
            f"The {image=} is a powershell image, does not have python version"
        )
        return None

    if python_version := DockerImagesMetadata.get_instance().python_version(image):
        return python_version
    logger.debug(
        f"Could not get python version for {image=} from {DOCKERFILES_INFO_REPO} repo"
    )

    if python_version := _get_python_version_from_tag_by_regex(image):
        return python_version
    logger.debug(f"Could not get python version for {image=} from regex")

    try:
        logger.debug(f"get python version for {image=} from dockerhub api")
        return _get_python_version_from_dockerhub_api(image)
    except Exception:
        logger.debug(
            f"Getting python version from {image=} by pulling its image and query its env"
        )
        return _get_python_version_from_image_client(image)


def _get_python_version_from_image_client(image: str) -> Version:
    """Get python version from docker image

    Args:
        image(str): Docker image id or name

    Returns:
        Version: Python version X.Y (3.7, 3.6, ..)
    """
    try:
        image = DockerBase.get_image_registry(image)
        image_model = DockerBase.pull_image(image)
        image_env = image_model.attrs["Config"]["Env"]
        logger.debug(f"Got {image_env=} from {image=}")
        return _get_python_version_from_env(image_env)
    except Exception:
        logger.exception(f"Failed detecting Python version for {image=}")
        raise


def _get_python_version_from_dockerhub_api(image: str) -> Version:
    """
    Get python version for a docker image from the dockerhub api

    Args:
        image (str): the docker image.

    Returns:
        Version: Python version X.Y (3.7, 3.6, ..)
    """
    if is_custom_registry():
        raise RuntimeError(
            f"Docker registry is configured to be {DOCKER_REGISTRY_URL}, unable to query the dockerhub api"
        )
    if ":" not in image:
        repo = image
        tag = "latest"
    elif image.count(":") > 1:
        raise ValueError(f"Invalid docker image: {image}")
    else:
        repo, tag = image.split(":")
    if os.getenv("CONTENT_GITLAB_CI"):
        # we need to remove the gitlab prefix, as we query the API
        repo = repo.replace(f"{DOCKER_REGISTRY_URL}/", "")
    try:
        token = _get_docker_hub_token(repo)
        digest = _get_image_digest(repo, tag, token)
        env = _get_image_env(repo, digest, token)
        return _get_python_version_from_env(env)
    except Exception as e:
        logger.error(
            f"Failed to get python version from docker hub for image {image}: {e}"
        )
        raise

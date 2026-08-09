import functools
import hashlib
import os
import re
import shutil
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import docker
import requests
import urllib3
from docker.types import Mount
from packaging.version import InvalidVersion, Version
from requests import JSONDecodeError
from requests.exceptions import RequestException

from demisto_sdk.commands.common.constants import (
    DEFAULT_DOCKER_REGISTRY_URL,
    DEFAULT_EXTENDED_REGISTRY,
    DEFAULT_PYTHON2_VERSION,
    DEFAULT_PYTHON_VERSION,
    DEMISTO_EXTENDED_REPOSITORY,
    DEMISTO_REPOSITORY,
    DEMISTO_SDK_EXTENDED_REGISTRY_ENV,
    DEVTEST_DEMISTO_EXTENDED_REPOSITORY,
    DEVTEST_DEMISTO_REPOSITORY,
    DOCKER_REGISTRY_URL,
    DOCKERFILES_INFO_REPO,
    TYPE_PWSH,
    TYPE_PYTHON,
    TYPE_PYTHON2,
    TYPE_PYTHON3,
    strip_cr_registry_prefix,
)
from demisto_sdk.commands.common.docker_images_metadata import DockerImagesMetadata
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import retry

IS_CONTENT_GITLAB_CI = os.getenv("CONTENT_GITLAB_CI")
DOCKER_IO = os.getenv("DOCKER_IO")
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

TEST_REQUIREMENTS_DIR = Path(__file__).parent.parent / "pre_commit" / "resources"
DOCKER_CONTAINER_TIMEOUT = int(os.getenv("DOCKER_CONTAINER_TIMEOUT") or 300)
EXTENDED_REPOSITORY_SEGMENT = f"{DEMISTO_EXTENDED_REPOSITORY}/"


class DockerException(Exception):
    pass


def init_global_docker_client(timeout: int = 60, log_prompt: str = ""):
    """
    Initialize and return a global Docker client to access and use a local Docker Daemon.

    This function initializes a global Docker client if it doesn't exist, or returns the existing one.
    It handles different environments, including GitLab CI, and attempts to log in to the Docker registry
    if credentials are available.

    Args:
        timeout (int, optional): The timeout for Docker client operations in seconds. Defaults to 60.
        log_prompt (str, optional): A prefix for log messages. Defaults to an empty string.

    Returns:
        docker.client.DockerClient: An initialized Docker client.

    Raises:
        docker.errors.DockerException: If initialization fails, likely due to Docker daemon not running.

    Behavior:
    1. Checks if a global Docker client already exists.
    2. If in GitLab CI environment, attempts to create a client using the job environment.
    3. If not in GitLab CI or if connecting via Gitlab CI environment fails,
       attempts to log in to the Docker registry if credentials are available.
    5. Logs various steps and outcomes of the initialization process.

    Note:
    - The function uses environment variables for Docker credentials.
    - It handles both standard and SSH-based Docker connections.
    """
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
            if IS_CONTENT_GITLAB_CI:
                """In the case of running in Gitlab CI environment, try to init a docker client from the
                job environment to utilize DockerHub API proxy requests (DOCKER_IO)"""
                logger.debug(
                    "Gitlab CI use case detected, trying to create docker client from Gitlab CI job environment."
                )
                DOCKER_CLIENT = docker.from_env(timeout=timeout)
                if DOCKER_CLIENT.ping():
                    # see https://docker-py.readthedocs.io/en/stable/client.html#docker.client.DockerClient.ping for more information about ping().
                    logger.debug(
                        "Successfully initialized docker client from Gitlab CI job environment."
                    )
                    return DOCKER_CLIENT
                else:
                    logger.warning(
                        f"{log_prompt} - Failed to init docker client in Gitlab CI use case."
                    )
        except docker.errors.DockerException:
            logger.warning(
                f"{log_prompt} - Failed to init docker client in CONTENT_GITLAB_CI use case. "
            )
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
            logger.debug(
                "One of docker_user or docker_pass is missing, skipping docker login"
            )
    else:
        msg = "docker client already available, using current DOCKER_CLIENT"
        logger.debug(f"{log_prompt} - {msg}" if log_prompt else msg)
    return DOCKER_CLIENT


def is_custom_registry():
    global DOCKER_REGISTRY_URL
    DOCKER_REGISTRY_URL = os.getenv(  # get the value from .env in runtime
        "DEMISTO_SDK_CONTAINER_REGISTRY",
        os.getenv("DOCKER_IO", DEFAULT_DOCKER_REGISTRY_URL),
    )

    return (
        not IS_CONTENT_GITLAB_CI and DOCKER_REGISTRY_URL != DEFAULT_DOCKER_REGISTRY_URL
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
    logger.debug("docker_helper | docker_login")
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
def gar_daemon_login(docker_client, registry: str) -> bool:
    """Log the Docker daemon into a GAR host so it can ``pull`` demistoextended
    images, using ``oauth2accesstoken`` + a gcloud access token. Returns True on
    success. (``docker_login`` only handles Docker Hub / custom user registries.)
    """
    # Imported lazily to avoid any import-time coupling with the HTTP client.
    from demisto_sdk.commands.common.docker.dockerhub_client import (
        get_gcloud_access_token,
    )

    token = get_gcloud_access_token()
    if not token:
        logger.warning(
            f"gar_daemon_login | no gcloud access token available, cannot log the "
            f"docker daemon in to {registry}"
        )
        return False
    try:
        docker_client.login(
            username="oauth2accesstoken",
            password=token,
            registry=registry,
        )
        logger.debug(
            f"gar_daemon_login | successfully logged the daemon in to {registry}"
        )
        return True
    except docker.errors.DockerException as e:
        logger.debug(
            f"gar_daemon_login | could not log the docker daemon in to {registry}: {e}"
        )
        return False


def _gar_registry_host(image: str) -> Optional[str]:
    """Return the image's GCR host (``gcr.io`` / ``*.gcr.io``) when it targets
    the extended registry and the Docker daemon needs a gcloud login before pull,
    or None otherwise. Matches on the exact host so lookalikes like
    ``gcr.io.evil.com`` are not misclassified.

    (The CI ``*.pkg.dev`` proxy is intentionally excluded: there the daemon is
    already logged in, so no extra ``gar_daemon_login`` is needed.)
    """
    host = image.split("/", 1)[0].lower()
    return host if host == "gcr.io" or host.endswith(".gcr.io") else None


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
    """
    Base class for Docker-related operations in the Demisto SDK.

    This class utilizes any environment where a Docker Daemon is initialized,
    and provides core functionality for working with Docker containers and images.

    Attributes:
        tmp_dir_name (tempfile.TemporaryDirectory): Temporary directory for Docker operations.
        tmp_dir (Path): Path object for the temporary directory.
        installation_scripts (dict): Mapping of container types to installation script paths.
        changes (dict): Docker image changes for different container types.
        requirements (Path): Path to the requirements.txt file.
        _files_to_push_on_installation (List[Tuple[os.PathLike, str]]): Files to be pushed during installation.

    Methods:
        version(): Get the Docker version.
        installation_files(container_type): Get installation files for a specific container type.
        pull_image(image): Pull a Docker image.
        is_image_available(image): Check if a Docker image is available.
        copy_files_container(container, files): Copy files to a Docker container.
        create_container(image, command, files_to_push, environment, **kwargs): Create a Docker container.
        push_image(image, log_prompt): Push a Docker image to the repository.
        create_image(base_image, image, container_type, install_packages, push, log_prompt): Create a new Docker image.
        get_image_registry(image): Get the full image name with registry.
        get_or_create_test_image(base_image, container_type, python_version, additional_requirements, push, should_pull, log_prompt): Get or create a test Docker image.
    """

    def __init__(self):
        global DOCKER_REGISTRY_URL
        DOCKER_REGISTRY_URL = os.getenv(  # get the value from .env in runtime
            "DEMISTO_SDK_CONTAINER_REGISTRY",
            os.getenv("DOCKER_IO", DEFAULT_DOCKER_REGISTRY_URL),
        )

        self.tmp_dir_name = tempfile.TemporaryDirectory(
            prefix=os.path.join(os.getcwd(), "tmp")
        )
        self.tmp_dir = Path(self.tmp_dir_name.name)
        installation_scripts = (
            Path(__file__).parent.parent
            / "pre_commit"
            / "resources"
            / "installation_scripts"
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

    @staticmethod
    @functools.lru_cache
    def version() -> Version:
        version = init_global_docker_client().version()["Version"]
        try:
            return Version(version)
        except InvalidVersion:
            # build number makes the version unable to parse, so we need to strip it
            return Version(version.split("-")[0])

    def installation_files(self, container_type: str) -> FILES_SRC_TARGET:
        files = self._files_to_push_on_installation.copy()
        files.append((self.installation_scripts[container_type], "/install.sh"))
        return files

    @staticmethod
    def pull_image(image: str) -> docker.models.images.Image:
        """
        Get a local docker image, or pull it when unavailable.
        """
        logger.debug(f"version is called with image={image}")
        docker_client = init_global_docker_client(log_prompt="pull_image")
        try:
            return docker_client.images.get(image)

        except docker.errors.ImageNotFound:
            logger.debug(f"docker {image=} not found locally, pulling")
            # The daemon has no gcloud credentials for GAR hosts, so log it in first.
            if gar_host := _gar_registry_host(image):
                gar_daemon_login(docker_client, gar_host)
            ret = docker_client.images.pull(image)
            logger.debug(f"pulled docker {image=} successfully")
            return ret

    @staticmethod
    def _is_image_available_on_registry(repo: str, tag: str) -> bool:
        """Check whether an image manifest exists on DockerHub via the Registry API.

        This queries the DockerHub Registry API directly, bypassing the local
        Docker daemon and any proxy/virtual registry configured in it.

        Args:
            repo (str): The repository name, e.g. ``devtestdemisto/python3``.
            tag (str): The image tag, e.g. ``3.10.0.12345-abcdef``.

        Returns:
            bool: True if the image manifest is available on DockerHub.

        Raises:
            RuntimeError: If the token or digest could not be obtained.
        """
        token = _get_docker_hub_token(repo)
        return bool(_get_image_digest(repo, tag, token))

    @staticmethod
    def is_image_available(
        image: str,
        use_registry_prefix: bool = False,
    ) -> bool:
        """Check whether an image is available.

        By default, this checks the local Docker daemon and falls back to the
        DockerHub Registry API. For images that live in a non-DockerHub registry
        (e.g. GAR-hosted ``devtestdemistoextended`` images), set
        ``use_registry_prefix=True`` to resolve the image through the configured
        registry (via :meth:`get_image_registry`) and pull it, instead of
        querying the DockerHub API which cannot see such images.

        Args:
            image (str): The image name, e.g. ``devtestdemisto/python3:1.0.0``.
            use_registry_prefix (bool): When True, verify availability by pulling
                the registry-qualified image instead of using the DockerHub API.

        Returns:
            bool: True if the image is available.
        """
        if use_registry_prefix:
            registry_image = DockerBase.get_image_registry(image)
            try:
                DockerBase.pull_image(registry_image)
                return True
            except (docker.errors.NotFound, docker.errors.ImageNotFound):
                logger.debug(f"Image {registry_image} not found in registry")
                return False

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
                    if DockerBase._is_image_available_on_registry(repo, tag):
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
        docker_client = init_global_docker_client(timeout=DOCKER_CONTAINER_TIMEOUT)

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

    def push_image(self, image: str, log_prompt: str = "") -> None:
        """This pushes the test image to dockerhub if the DOCKERHUB env variables are set
        Args:
            image (str): The image to push
            log_prompt (str, optional): The log prompt to print. Defaults to "".
        """
        test_image_name_to_push = image.replace(f"{DOCKER_REGISTRY_URL}/", "")

        logger.info(
            f"{log_prompt} - Trying to push Image {test_image_name_to_push} to repository."
        )
        push_succeeded = False
        for attempt in range(2):
            try:
                docker_push_output = init_global_docker_client().images.push(
                    test_image_name_to_push
                )
                logger.debug(
                    f"{log_prompt} - Push details for image {test_image_name_to_push}: {docker_push_output}"
                )
                outputs_lines = docker_push_output.strip().split("\r\n")
                error_line = next(
                    filter(lambda line: "errorDetail" in line, outputs_lines), None
                )
                if error_line:
                    logger.error(
                        f"{log_prompt} - Error pushing image {test_image_name_to_push}: {error_line}"
                    )
                    raise DockerException(
                        f"Failed to push image {test_image_name_to_push} to repository."
                    )
                else:
                    logger.success(
                        f"{log_prompt} - Attempt {attempt + 1}: Successfully pushed image {test_image_name_to_push} to repository."
                    )
                push_succeeded = True
                break
            except (
                requests.exceptions.ConnectionError,
                urllib3.exceptions.ReadTimeoutError,
                requests.exceptions.ReadTimeout,
            ) as e:
                logger.warning(
                    f"{log_prompt} - Attempt {attempt + 1}: Failed to push image {test_image_name_to_push} to repository due to {type(e).__name__}",
                    exc_info=True,
                )

        if not push_succeeded:
            raise DockerException(
                f"{log_prompt} - All push attempts failed for image {test_image_name_to_push}."
            )

        # After a successful push, verify the image is pullable from the registry.
        # Registry propagation can take a few minutes, so we retry with delays.
        self._verify_image_available_after_push(
            test_image_name_to_push, log_prompt=log_prompt
        )

    @staticmethod
    def _verify_image_available_after_push(
        image: str,
        log_prompt: str = "",
        max_retries: int = 10,
        delay_seconds: int = 30,
    ) -> None:
        """Verify a pushed image is available in its registry.

        After pushing, the registry may take a few minutes to propagate the image.
        For DockerHub-hosted images this queries the DockerHub Registry API
        directly (bypassing any proxy/virtual registry configured in the Docker
        daemon). For images hosted in a non-DockerHub registry (e.g. GAR-hosted
        ``devtestdemistoextended`` images), the DockerHub API cannot see them, so
        verification is done by resolving and pulling the registry-qualified
        image via :meth:`is_image_available`.

        Args:
            image (str): The image name (without registry prefix), e.g.
                ``devtestdemisto/python3:3.10.0.12345-abcdef``.
            log_prompt (str): Log prompt prefix for messages.
            max_retries (int): Maximum number of verification attempts. Defaults to 10.
            delay_seconds (int): Seconds to wait between retries. Defaults to 30.
        """
        if ":" not in image:
            repo, tag = image, "latest"
        elif image.count(":") > 1:
            raise ValueError(f"Invalid docker image: {image}")
        else:
            repo, tag = image.split(":")

        # Extended (``devtestdemistoextended/*``) images are hosted ONLY on GCR
        # (``gcr.io/xsoar-registry``) and are not visible via the DockerHub Registry
        # API, so they must be verified through the configured registry (daemon
        # pull). Regular ``devtestdemisto/*`` images are pushed to and served from
        # DockerHub, so they are verified via the DockerHub Registry API directly -
        # which queries DockerHub itself, bypassing any DockerHub pull-through proxy
        # (e.g. the CI ``xdr-docker-hub-virtual`` GAR proxy) that cannot serve a
        # freshly pushed tag.
        is_gar_image = repo.startswith(DEVTEST_DEMISTO_EXTENDED_REPOSITORY)
        registry_name = "the registry (GAR)" if is_gar_image else "DockerHub"

        logger.info(
            f"{log_prompt} - Verifying pushed image {image} is available on "
            f"{registry_name} (up to {max_retries} attempts, {delay_seconds}s apart)."
        )

        for attempt in range(1, max_retries + 1):
            try:
                if is_gar_image:
                    if not DockerBase.is_image_available(
                        image, use_registry_prefix=True
                    ):
                        raise RuntimeError(
                            f"Image {image} not yet available in registry"
                        )
                elif not DockerBase._is_image_available_on_registry(repo, tag):
                    raise RuntimeError(
                        f"Image {image} not yet available on {registry_name}"
                    )
                logger.success(
                    f"{log_prompt} - Image verification succeeded for {image} "
                    f"on attempt {attempt}."
                )
                return
            except RuntimeError:
                logger.info(
                    f"{log_prompt} - Verification attempt {attempt}/{max_retries}: "
                    f"image {image} not yet available on {registry_name}. "
                    f"Retrying in {delay_seconds}s..."
                )
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                RequestException,
                docker.errors.APIError,
            ) as e:
                logger.warning(
                    f"{log_prompt} - Verification attempt {attempt}/{max_retries}: "
                    f"failed due to {type(e).__name__}. Retrying in {delay_seconds}s...",
                    exc_info=True,
                )

            if attempt < max_retries:
                time.sleep(delay_seconds)

        raise DockerException(
            f"{log_prompt} - Image verification failed: {image} was not found on {registry_name} "
            f"after {max_retries} attempts "
            f"(~{(max_retries - 1) * delay_seconds}s of delay between attempts, "
            f"excluding request time). "
            f"The registry may not have propagated the image in time."
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
            2. running the installation scripts
            3. committing the docker changes (installed packages) to a new local image
        """
        logger.debug(
            f"create_image is called with base_image={base_image}, image={image}"
        )
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
        repository, tag = image.rsplit(
            ":", 1
        )  # rsplit is used to support non-default docker ports which require extra colon. i.e: `image.registry:5000/repo/some-image:main`
        if IS_CONTENT_GITLAB_CI:
            repository = repository.replace(f"{DOCKER_REGISTRY_URL}/", "")

        container.commit(
            repository=repository, tag=tag, changes=self.changes[container_type]
        )
        if push and IS_CONTENT_GITLAB_CI:
            self.push_image(image, log_prompt=log_prompt)
        return image

    @staticmethod
    def get_image_registry(image: str) -> str:
        # TEMPORARY (CIAC-17352): content may currently send images already prefixed
        # with the CR host; strip it back to the canonical form so we re-add the
        # correct registry below. Remove this line once content stops prefixing.
        image = strip_cr_registry_prefix(image)
        # "demistoextended" images -> extended (GAR) registry; everything else -> Docker.
        registry = (
            os.getenv(DEMISTO_SDK_EXTENDED_REGISTRY_ENV, DEFAULT_EXTENDED_REGISTRY)
            if DEMISTO_EXTENDED_REPOSITORY in image
            else DOCKER_REGISTRY_URL
        )
        if registry and registry not in image:
            return f"{registry}/{image}"
        return image

    @staticmethod
    def get_test_image_registry(image: str) -> str:
        """Resolve the registry for a *dev/test* image that we build, push and then
        immediately pull back.

        Unlike base images (which are pre-existing and may safely be pulled through
        a Docker Hub pull-through proxy), a dev/test image is created seconds before
        it is consumed. It must therefore be pulled from the exact registry it was
        pushed to, otherwise a pull-through proxy - which has not yet fetched the
        brand-new tag - answers ``manifest unknown`` and the docker hooks fail on
        first-time pushes (they only succeed on a later retry, once the proxy has
        caught up).

        ``devtestdemistoextended/*`` images live only in the extended (GAR) registry,
        so they keep their registry prefix. Regular ``devtestdemisto/*`` images are
        pushed to Docker Hub, so they are left unqualified and pulled straight from
        Docker Hub - keeping the push target and the pull target identical.
        """
        image = strip_cr_registry_prefix(image)
        if DEMISTO_EXTENDED_REPOSITORY not in image:
            return image
        # Extended images resolve to the same registry as any other extended image.
        return DockerBase.get_image_registry(image)

    @staticmethod
    def build_test_image_name(base_image: str, identifier: str) -> str:
        """Build the dev/test image name, mapping extended images to devtestdemistoextended/."""
        if base_image.startswith(EXTENDED_REPOSITORY_SEGMENT):
            renamed = base_image.replace(
                DEMISTO_EXTENDED_REPOSITORY, DEVTEST_DEMISTO_EXTENDED_REPOSITORY
            )
        else:
            renamed = base_image.replace(DEMISTO_REPOSITORY, DEVTEST_DEMISTO_REPOSITORY)
        return f"{renamed}-{identifier}"

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
            pip_requirements = pip_requirements + additional_requirements
        identifier = hashlib.md5(
            "\n".join(sorted(set(pip_requirements))).encode("utf-8")
        ).hexdigest()

        test_docker_image = self.build_test_image_name(base_image, identifier)
        if is_custom_registry():
            # if we use a custom registry, we need to have to pull the image and we can't use dockerhub api
            should_pull = True
        if not should_pull and self.is_image_available(test_docker_image):
            return test_docker_image, errors
        # The base image already exists, so it may safely be pulled through the
        # configured (proxy) registry. The dev/test image, however, is pushed and
        # then immediately pulled back, so it must resolve to the same registry it
        # was pushed to - see get_test_image_registry.
        base_image = self.get_image_registry(base_image)
        test_docker_image = self.get_test_image_registry(test_docker_image)

        try:
            logger.debug(
                f"{log_prompt} - Trying to pull existing image {test_docker_image}"
            )
            self.pull_image(test_docker_image)
        except docker.errors.DockerException:
            # DockerException is the base class (APIError, ImageNotFound, and
            # credential-store failures such as a missing docker-credential-gcloud),
            # so a failed GAR pull falls back to building instead of crashing.
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
                if EXTENDED_REPOSITORY_SEGMENT in base_image:
                    # GAR images may legitimately fail (e.g. no credentials); log at
                    # debug and return `errors` for the caller to skip or fail.
                    logger.debug(
                        f"{log_prompt} - could not prepare {base_image}: {errors}"
                    )
                else:
                    logger.exception(  # noqa: PLE1205
                        "{}",
                        f"<red>{log_prompt} - Build errors occurred: {errors}</red>",
                    )
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
    logger.debug("docker_helper | _get_python_version_from_tag_by_regex")
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

    if EXTENDED_REPOSITORY_SEGMENT in image:
        try:
            from demisto_sdk.commands.common.docker.docker_image import DockerImage

            if python_version := DockerImage(image).python_version:
                return python_version
            logger.warning(
                f"get_python_version | extended {image=} returned no python version"
            )
        except Exception as e:
            logger.warning(
                f"Could not get python version for extended {image=} from its registry: {e}"
            )
        return None

    if IS_CONTENT_GITLAB_CI:
        try:
            logger.debug(
                f"get python version for {image=} from available docker client"
            )
            return _get_python_version_from_image_client(image)
        except Exception:
            logger.debug(
                f"Could not get python version for {image=} from available docker client"
            )

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
    if IS_CONTENT_GITLAB_CI:
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

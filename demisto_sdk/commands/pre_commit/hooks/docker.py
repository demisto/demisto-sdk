import functools
import os
import shutil
import subprocess
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import more_itertools
from docker.errors import DockerException
from packaging.version import Version
from requests import Timeout

from demisto_sdk.commands.common.constants import (
    TYPE_PWSH,
    TYPE_PYTHON,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.docker_helper import (
    DockerBase,
    docker_login,
    get_docker,
    get_pip_requirements_from_file,
    init_global_docker_client,
)
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
)
from demisto_sdk.commands.common.tools import logger
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.pre_commit.hooks.hook import GeneratedHooks, Hook


class DockerImageFlagOption(Enum):
    FROM_YML = "from-yml"
    NATIVE = "native:"
    NATIVE_DEV = "native:dev"
    NATIVE_GA = "native:ga"
    NATIVE_MAINTENANCE = "native:maintenance"
    ALL_IMAGES = "all"
    NATIVE_TARGET = "native:target"
    NATIVE_CANDIDATE = "native:candidate"


NO_SPLIT = None

IMAGES_BATCH = int(os.getenv("IMAGES_BATCH") or 40)


def get_mypy_requirements():
    """
    Retrieves the mypy requirements from a local file or from GitHub.

    If the local `mypy-requirements.txt` file exists, it reads the requirements from the file.
    Otherwise, it attempts to fetch the requirements from GitHub.

    Returns:
        List[str]: A list of requirements.

    Raises:
        RuntimeError: If the requirements cannot be read from GitHub.
    """
    mypy_requirements_path = Path(f"{CONTENT_PATH}/mypy-requirements.txt")
    if mypy_requirements_path.exists():
        requirements = get_pip_requirements_from_file(mypy_requirements_path)
    else:
        try:
            requirements = TextFile.read_from_github_api(
                "mypy-requirements.txt", verify_ssl=False
            ).split("\n")
            logger.debug("Retrieved mypy requirements from demisto/content repository.")
        except (FileReadError, ConnectionError, Timeout) as e:
            raise RuntimeError(
                "Could not read mypy-requirements.txt from Github"
            ) from e
    # Remove comments and empty lines
    return [
        req.strip()
        for req in requirements
        if req.strip() and not req.strip().startswith("#")
    ]


@lru_cache()
def get_docker_python_path(drop_site_packages: bool = False) -> str:
    """
    precommit by default mounts the content repo to source.
    drop_site_packages is used for building MYPYPATH
    This means CommonServerPython's path is /src/Packs/Base/...CSP.py
    Returns: A PYTHONPATH formatted string
    """
    path_to_replace = str(Path(CONTENT_PATH).absolute())
    docker_path = [str(path).replace(path_to_replace, "/src") for path in PYTHONPATH]
    if drop_site_packages:
        docker_path = [p for p in docker_path if "site-packages" not in p]
    path = ":".join(docker_path)
    logger.debug(f"pythonpath in docker being set to {path}")
    return path


def with_native_tags(
    tags_to_files: Dict[str, List[Tuple[Path, IntegrationScript]]],
    docker_flags: Set[str],
    docker_image: Optional[str],
) -> Dict[str, List[Tuple[Path, IntegrationScript]]]:
    """
    Adds the native image images into the dict with the files that should be run on them
    Args:
        tags_to_files: Dict[str, Tuple[str, dict] the incoming dict without native image of files split according to the docker images
        docker_image_flag: the flag from the config file. all/native:ga/native:maintenance etc

    Returns: The updated dict with the native images.

    """

    all_tags_to_files = defaultdict(list)
    is_native_image = any(
        DockerImageFlagOption.NATIVE.value in docker_flag
        for docker_flag in docker_flags
    )

    for image, scripts in tags_to_files.items():
        for file, obj in scripts:
            if is_native_image:
                native_image_config = NativeImageConfig.get_instance()
                supported_native_images = ScriptIntegrationSupportedNativeImages(
                    _id=obj.object_id,
                    native_image_config=native_image_config,
                    docker_image=image,
                ).get_supported_native_docker_tags(docker_flags, include_candidate=True)

                for native_image in supported_native_images:
                    all_tags_to_files[docker_image or native_image].append((file, obj))
            if {
                DockerImageFlagOption.FROM_YML.value,
                DockerImageFlagOption.ALL_IMAGES.value,
            } & docker_flags:
                all_tags_to_files[docker_image or image].append((file, obj))

    return all_tags_to_files


def docker_tag_to_runfiles(
    files_to_run: Iterable[Tuple[Path, Optional[IntegrationScript]]],
    docker_image_flag: str,
    docker_image: Optional[str] = None,
) -> Dict[str, List[Tuple[Path, IntegrationScript]]]:
    """
    Iterates over all files snf groups the files by the dockerimages
    Args:
        files_to_run: PosixFiles to run the command on
        docker_image_flag: the docker_image config value

    Returns: A dict of image to List of files(Tuple[path, obj]) including native images

    """
    docker_flags = set(docker_image_flag.split(","))
    tags_to_files = defaultdict(list)
    for file, obj in files_to_run:
        if obj:
            for image in obj.docker_images:
                tags_to_files[image].append((file, obj))

    return with_native_tags(tags_to_files, docker_flags, docker_image)


@functools.lru_cache(maxsize=512)
def devtest_image(
    image_tag: str,
    is_powershell: bool,
    should_pull: bool,
    should_install_mypy_additional_dependencies: Optional[bool],
) -> str:
    """
    We need to add test dependencies on the image. In the future we could add "additional_dependencies" as a template
    config arg and pass it through here
    Args:
        image_tag: the base image tag
        is_powershell: if the image is a powershell based image
        should_pull: if true, don't pull images on background
        should_install_mypy_additional_dependencies: if true the mypy types dependencies
    Returns: The build and pulled dev image

    """
    docker_base = get_docker()
    image, errors = docker_base.get_or_create_test_image(
        base_image=image_tag,
        container_type=TYPE_PWSH if is_powershell else TYPE_PYTHON,
        push=docker_login(docker_client=init_global_docker_client()),
        should_pull=False,
        log_prompt="DockerHook",
        additional_requirements=get_mypy_requirements()
        if should_install_mypy_additional_dependencies
        else None,
    )
    if not errors:
        if not should_pull:
            # pull images in background
            if os.getenv("CONTENT_GITLAB_CI"):
                # When running from Gitlab CI
                docker_user = os.getenv("DOCKERHUB_USER", "")
                docker_pass = os.getenv("DOCKERHUB_PASSWORD", "")
                login_command = [
                    "docker",
                    "login",
                    "-u",
                    docker_user,
                    "-p",
                    docker_pass,
                ]
                subprocess.run(
                    login_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            subprocess.Popen(
                ["docker", "pull", image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return image
    raise DockerException(errors)


def compose_docker_environment_variables(env: dict, mypy_path: bool = False) -> str:
    """
    The env needed to run python scripts in docker
    """
    env_vars = {"PYTHONPATH": get_docker_python_path(), **env}

    if mypy_path:
        env_vars["MYPYPATH"] = get_docker_python_path(drop_site_packages=True)

    if os.getenv("GITHUB_ACTIONS"):
        env_vars["GITHUB_ACTIONS"] = "true"

    return " ".join(f' --env "{key}={value}"' for key, value in env_vars.items())


def _split_by_objects(
    files_with_objects: List[Tuple[Path, IntegrationScript]],
    config_arg: Optional[Tuple[str, str]],
    run_isolated: bool = False,
) -> Dict[Optional[IntegrationScript], Set[Tuple[Path, IntegrationScript]]]:
    """
    Will group files into groups that share the same configuration file.
    If there is no config file, they get set to the NO_CONFIG_VALUE group
    Args:
        files: the files to split
        config_arg: a tuple, argument_name, file_name
        run_isolated: a boolean. If true it will split all the objects into separate hooks.

    Returns:
        a dict where the keys are the names of the folder of the config and the value is a set of files for that config
    """
    object_to_files: Dict[
        Optional[IntegrationScript], Set[Tuple[Path, IntegrationScript]]
    ] = defaultdict(set)
    config_filename = (config_arg or ("", ""))[1]
    for file, obj in files_with_objects:
        if run_isolated or (
            config_arg and (obj.path.parent / config_filename).exists()
        ):
            object_to_files[obj].add((file, obj))

        else:
            object_to_files[NO_SPLIT].add((file, obj))

    return object_to_files


class DockerHook(Hook):
    """
    This class will make common manipulations on commands that need to run in docker
    """

    def clean_args_from_hook(self, hooks: List[Dict]):
        """This clean unsupported args from the generated hooks

        Args:
            hooks (List[Dict]): The hooks generated
        """
        for hook in hooks:
            hook.pop("docker_image", None)
            hook.pop("config_file_arg", None)
            hook.pop("copy_files", None)
            hook.pop("run_isolated", None)
            hook.pop("pass_docker_extra_args", None)

    def process_image(
        self,
        image: str,
        files_with_objects: List[Tuple[Path, IntegrationScript]],
        config_arg: Optional[Tuple[str, str]],
        run_isolated: bool,
    ) -> List[Dict]:
        """
        Process the image and files to run on it, and returns the generated hooks

        Args:
            image (str): The image to process
            files_with_objects (List[Tuple[Path, IntegrationScript]]): The files to run on the image
            config_arg (Optional[Tuple]): The config arg to set where relevant. This will be appended to the end of "args"
            run_isolated (bool): Whether to run the files in isolated containers

        Returns:
            List[Dict]: List of generated hooks.
        """
        object_to_files = _split_by_objects(
            files_with_objects,
            config_arg,
            run_isolated,
        )
        is_image_powershell = any(obj.is_powershell for _, obj in files_with_objects)
        mypy_additional_dependencies = self.base_hook.get(
            "name", ""
        ).startswith(  # see CIAC-11832
            "mypy-in-docker"
        )
        dev_image = devtest_image(
            image,
            is_image_powershell,
            self.context.dry_run,
            mypy_additional_dependencies,
        )
        hooks = self.generate_hooks(dev_image, image, object_to_files, config_arg)
        logger.debug(f"Generated {len(hooks)} hooks for image {image}")
        return hooks

    def prepare_hook(
        self,
    ) -> GeneratedHooks:
        """
        Group all the files by dockerimages
        Split those images by config files
        Get the devimage for each image
        Args:
        """

        start_time = time.time()
        filtered_files = self.filter_files_matching_hook_config(
            (file for file, _ in self.context.files_to_run_with_objects)
        )
        if not filtered_files:
            logger.debug(
                "No files matched docker hook filter, skipping docker preparation"
            )
            return []
        filtered_files_with_objects = {
            (file, obj)
            for file, obj in self.context.files_to_run_with_objects
            if file in filtered_files
        }
        tag_to_files_objs = docker_tag_to_runfiles(
            filtered_files_with_objects,
            self.context.docker_image or self._get_property("docker_image", "from-yml"),
            self.context.image_ref,
        )
        end_time = time.time()
        logger.debug(
            f"Elapsed time to gather tags to files: {end_time - start_time} seconds"
        )
        if copy_files := self._get_property("copy_files"):
            all_objects = {obj for _, obj in filtered_files_with_objects if obj}
            for obj in all_objects:
                for file in copy_files:
                    source: Path = CONTENT_PATH / file
                    target = obj.path.parent / Path(file).name
                    if source != target and source.exists() and not target.exists():
                        shutil.copy(
                            CONTENT_PATH / file, obj.path.parent / Path(file).name
                        )
        run_isolated = self._get_property("run_isolated", False)
        config_arg = self._get_config_file_arg()
        start_time = time.time()
        logger.debug(f"{len(tag_to_files_objs)} images were collected from files")
        logger.debug(
            f'collected images: {" ".join(filter(None, tag_to_files_objs.keys()))}'
        )
        docker_hook_ids = []
        results: List[List[Dict]] = []

        for chunk in more_itertools.chunked(
            sorted(tag_to_files_objs.items()), IMAGES_BATCH
        ):
            with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
                # process images in batches to avoid memory issues
                results.extend(
                    executor.map(
                        lambda item: self.process_image(
                            item[0], item[1], config_arg, run_isolated
                        ),
                        chunk,
                    )
                )
        for hooks in results:
            self.hooks.extend(hooks)
            docker_hook_ids.extend([hook["id"] for hook in hooks])

        end_time = time.time()
        logger.debug(
            f"DockerHook - prepared images in {round(end_time - start_time, 2)} seconds"
        )

        return GeneratedHooks(hook_ids=docker_hook_ids, parallel=self.parallel)

    def generate_hooks(
        self,
        dev_image,
        image,
        object_to_files_with_objects: Dict[
            Optional[IntegrationScript], Set[Tuple[Path, IntegrationScript]]
        ],
        config_arg: Optional[Tuple],
    ):
        """
        Given the docker image and files to run on it, create new hooks to insert
        Args:
            dev_image: The actual image to run on
            image: name of the base image (for naming)
            object_to_files_with_objects: A dict where the key is the object (or None) and value is the set of files to run together.
            config_arg: The config arg to set where relevant. This will be appended to the end of "args"

        Returns:
            All the hooks to be appended for this image
        """
        new_hook = deepcopy(self.base_hook)

        new_hook["id"] = f"{new_hook.get('id')}-{image}"
        new_hook["name"] = f"{new_hook.get('name')}-{image}"
        new_hook["language"] = "docker_image"
        env = new_hook.pop("env", {})
        docker_version = DockerBase.version()
        quiet = True
        # quiet mode silently pulls the image, and it is supported only above 19.03
        if docker_version < Version("19.03"):
            quiet = False
        docker_extra_args = self._get_property("pass_docker_extra_args", "")
        new_hook["entry"] = (
            f'--entrypoint {new_hook.get("entry")} {docker_extra_args} {compose_docker_environment_variables(env,mypy_path=new_hook["name"].startswith("mypy-in-docker"))} {"--quiet" if quiet else ""} {dev_image}'
        )
        ret_hooks = []
        for (
            integration_script,
            files_with_objects,
        ) in object_to_files_with_objects.items():
            change_working_directory = False
            files = {file for file, _ in files_with_objects}
            objects_ = [object_ for _, object_ in files_with_objects]
            hook = deepcopy(new_hook)
            if new_hook["name"].startswith("mypy-in-docker"):  # see CIAC-11832
                for obj in objects_:
                    python_version = Version(obj.python_version)
                    hook["args"].append(
                        f"--python-version={python_version.major}.{python_version.minor}"
                    )  # mypy expects only the major and minor version (e.g., 3.10)
            if integration_script is not None:
                change_working_directory = (
                    True  # isolate container, so run in the same directory
                )
                if config_arg:
                    args = deepcopy(self._get_property("args", []))
                    args.extend(
                        [
                            config_arg[0],
                            str(
                                Path("/src")
                                / (
                                    integration_script.path.parent / config_arg[1]
                                ).relative_to(CONTENT_PATH)
                            ),
                        ]
                    )
                    hook["args"] = args
                hook["id"] = (
                    f"{hook['id']}-{integration_script.object_id}"  # for uniqueness
                )
                hook["name"] = (
                    f"{hook['name']}-{integration_script.object_id}"  # for uniqueness
                )
                # change the working directory to the integration script, as it runs in an isolated container
                hook["entry"] = (
                    f"-w {Path('/src') / integration_script.path.parent.relative_to(CONTENT_PATH)} {hook['entry']}"
                )

            if self._set_files_on_hook(
                hook,
                files,
                should_filter=False,
                use_args=change_working_directory,
                base_path=Path("/src"),
            ):  # no need to filter again, we have only filtered files
                # disable multiprocessing on hook
                hook["require_serial"] = True
                ret_hooks.append(hook)
        self.clean_args_from_hook(ret_hooks)
        return ret_hooks

    def _get_config_file_arg(self) -> Optional[Tuple[str, str]]:
        """
        A config arg should be of the format
            config_file_arg:
                arg_name: '--argname'
                file_name: '.filename'
        Returns: argname, filename

        """
        if config_arg := self._get_property("config_file_arg"):
            arg_name = config_arg.get("arg_name")
            file_name = config_arg.get("file_name")
            if not arg_name or not file_name:
                raise ValueError(
                    f"config_file_arg was provided in pre-commit hook with id {self._get_property('id')}"
                    "  in configuration file but not properly formed. Must have arg_name and file_name keys"
                )
            return arg_name, file_name
        return None

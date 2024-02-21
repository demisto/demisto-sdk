import functools
import os
import shutil
import subprocess
import time
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache, partial
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import more_itertools
from docker.errors import DockerException
from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    TESTS_REQUIRE_NETWORK_PACK_IGNORE,
    TYPE_PWSH,
    TYPE_PYTHON,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.docker_helper import (
    docker_login,
    get_docker,
    init_global_docker_client,
)
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
)
from demisto_sdk.commands.common.tools import logger
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.lint.linter import DockerImageFlagOption
from demisto_sdk.commands.pre_commit.hooks.hook import Hook

NO_SPLIT = None


@lru_cache()
def get_docker_python_path() -> str:
    """
    precommit by default mounts the content repo to source.
    This means CommonServerPython's path is /src/Packs/Base/...CSP.py
    Returns: A PYTHONPATH formatted string
    """
    path_to_replace = str(Path(CONTENT_PATH).absolute())
    docker_path = [str(path).replace(path_to_replace, "/src") for path in PYTHONPATH]
    path = ":".join(docker_path)
    logger.debug(f"pythonpath in docker being set to {path}")
    return path


def with_native_tags(
    tags_to_files: Dict[str, List[Tuple[Path, IntegrationScript]]],
    docker_image_flag: str,
) -> Dict[str, List[Tuple[Path, IntegrationScript]]]:
    """
    Adds the native image images into the dict with the files that should be run on them
    Args:
        tags_to_files: Dict[str, Tuple[str, dict] the incoming dict without native image of files split according to the docker images
        docker_image_flag: the flag from the config file. all/native:ga/native:maintenance etc

    Returns: The updated dict with the native images.

    """
    docker_flags = set(docker_image_flag.split(","))
    all_tags_to_files = defaultdict(list)
    native_image_config = NativeImageConfig.get_instance()

    for image, scripts in tags_to_files.items():
        for file, obj in scripts:

            supported_native_images = ScriptIntegrationSupportedNativeImages(
                _id=obj.object_id,
                native_image_config=native_image_config,
                docker_image=image,
            ).get_supported_native_docker_tags(docker_flags)
            for native_image in supported_native_images:
                all_tags_to_files[native_image].append((file, obj))
            if {
                DockerImageFlagOption.FROM_YML.value,
                DockerImageFlagOption.ALL_IMAGES.value,
            } & docker_flags:
                all_tags_to_files[image].append((file, obj))
    return all_tags_to_files


def docker_tag_to_runfiles(
    files_to_run: Iterable[Tuple[Path, Optional[IntegrationScript]]], docker_image_flag
) -> Dict[str, List[Tuple[Path, IntegrationScript]]]:
    """
    Iterates over all files snf groups the files by the dockerimages
    Args:
        files_to_run: PosixFiles to run the command on
        docker_image_flag: the docker_image config value

    Returns: A dict of image to List of files(Tuple[path, obj]) including native images

    """
    tags_to_files = defaultdict(list)
    for file, obj in files_to_run:
        if not obj:
            continue
        for docker_image in obj.docker_images:
            tags_to_files[docker_image].append((file, obj))
    return with_native_tags(tags_to_files, docker_image_flag)


@functools.lru_cache(maxsize=512)
def devtest_image(
    image_tag: str,
    is_powershell: bool,
    should_pull: bool,
) -> str:
    """
    We need to add test dependencies on the image. In the future we could add "additional_dependencies" as a template
    config arg and pass it through here
    Args:
        image_tag: the base image tag
        is_powershell: if the image is a powershell based image
        should_pull: if true, don't pull images on background
    Returns: The build and pulled dev image

    """
    docker_base = get_docker()
    image, errors = docker_base.get_or_create_test_image(
        base_image=image_tag,
        container_type=TYPE_PWSH if is_powershell else TYPE_PYTHON,
        push=docker_login(docker_client=init_global_docker_client()),
        should_pull=False,
        log_prompt="DockerHook",
    )
    if not errors:
        if not should_pull:
            # pull images in background
            subprocess.Popen(
                ["docker", "pull", image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return image
    raise DockerException(errors)


def get_environment_flag(env: dict) -> str:
    """
    The env flag needed to run python scripts in docker
    """
    env_flag = f'--env "PYTHONPATH={get_docker_python_path()}"'
    for key, value in env.items():
        env_flag += f' --env "{key}={value}"'
    if os.getenv("GITHUB_ACTIONS"):
        env_flag += " --env GITHUB_ACTIONS=true"
    return env_flag


def _split_by_objects(
    files_with_objects: List[Tuple[Path, IntegrationScript]],
    config_arg: Optional[Tuple],
    isolate_container: bool = False,
    support_pack_ignore_config: bool = False,
) -> Dict[Optional[IntegrationScript], Set[Tuple[Path, IntegrationScript]]]:
    """
    Will group files into groups that share the same configuration file.
    If there is no config file, they get set to the NO_CONFIG_VALUE group
    Args:
        files: the files to split
        config_arg: a tuple, argument_name, file_name
        isolate_container: a boolean. If true it will split all the objects into separate hooks.
        support_pack_ignore_config: a boolean. If true it will read the support the config in pack ignore, for example networking.

    Returns:
        a dict where the keys are the names of the folder of the config and the value is a set of files for that config
    """
    object_to_files: Dict[
        Optional[IntegrationScript], Set[Tuple[Path, IntegrationScript]]
    ] = defaultdict(set)

    for file, obj in files_with_objects:
        if (
            isolate_container
            or (config_arg and (obj.path.parent / config_arg[1]).exists())
            or (support_pack_ignore_config and should_enable_network(obj))
        ):
            object_to_files[obj].add((file, obj))

        else:
            object_to_files[NO_SPLIT].add((file, obj))

    return object_to_files


@lru_cache
def should_enable_network(integration_script: Optional[IntegrationScript]) -> bool:
    if not integration_script:
        return False
    pack = integration_script.in_pack
    if pack and (ignored_errors_dict := pack.ignored_errors_dict):
        if TESTS_REQUIRE_NETWORK_PACK_IGNORE in ignored_errors_dict:
            ignored_integrations_scripts_ids = ignored_errors_dict[
                TESTS_REQUIRE_NETWORK_PACK_IGNORE
            ]
            if integration_script.object_id in ignored_integrations_scripts_ids:
                return True
    return False


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
            hook.pop("isolate_container", None)
            hook.pop("support_pack_ignore_config", None)

    def process_image(
        self,
        image_files_with_objects: Tuple[str, List[Tuple[Path, IntegrationScript]]],
        config_arg: Optional[Tuple],
        isolate_container: bool,
        support_pack_ignore_config: bool,
    ) -> List[Dict]:
        image, files_with_objects = image_files_with_objects
        object_to_files = _split_by_objects(
            files_with_objects,
            config_arg,
            isolate_container,
            support_pack_ignore_config,
        )
        image_is_powershell = any(obj.is_powershell for _, obj in files_with_objects)

        dev_image = devtest_image(image, image_is_powershell, self.context.dry_run)
        hooks = self.get_new_hooks(
            dev_image, image, object_to_files, config_arg, support_pack_ignore_config
        )
        return hooks

    def prepare_hook(
        self,
    ):
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
            return
        filtered_files_with_objects = {
            (file, obj)
            for file, obj in self.context.files_to_run_with_objects
            if file in filtered_files
        }
        tag_to_files_objs = docker_tag_to_runfiles(
            filtered_files_with_objects,
            self._get_property("docker_image", "from-yml"),
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
        isolate_container = self._get_property("isolate_container", False)
        support_pack_ignore_config = self._get_property(
            "support_pack_ignore_config", False
        )
        config_arg = self._get_config_file_arg()
        start_time = time.time()
        logger.debug(f"{len(tag_to_files_objs)} images were collected from files")
        logger.debug(f'collected images: {" ".join(tag_to_files_objs.keys())}')

        with Pool(processes=cpu_count()) as pool:
            hooks = pool.map(
                partial(
                    self.process_image,
                    config_arg=config_arg,
                    isolate_container=isolate_container,
                    support_pack_ignore_config=support_pack_ignore_config,
                ),
                sorted(tag_to_files_objs.items(), key=lambda item: item[0]),
            )
            self.hooks = list(more_itertools.flatten(hooks))
        end_time = time.time()
        logger.debug(
            f"DockerHook - prepared images in {round(end_time - start_time, 2)} seconds"
        )

    def get_new_hooks(
        self,
        dev_image,
        image,
        object_to_files_with_objects: Dict[
            Optional[IntegrationScript], Set[Tuple[Path, IntegrationScript]]
        ],
        config_arg: Optional[Tuple],
        support_pack_ignore_config,
    ):
        """
        Given the docker image and files to run on it, create new hooks to insert
        Args:
            dev_image: The actual image to run on
            image: name of the base image (for naming)
            object_to_files_with_objects: A dict where the key is the object (or None) and value is the set of files to run together.
            config_arg: The config arg to set where relevant. This will be appended to the end of "args"
            support_pack_ignore_config: a boolean. If true it will read the support the config in pack ignore, for example networking.

        Returns:
            All the hooks to be appended for this image
        """
        new_hook = deepcopy(self.base_hook)
        new_hook["id"] = f"{new_hook.get('id')}-{image}"
        new_hook["name"] = f"{new_hook.get('name')}-{image}"
        new_hook["language"] = "docker_image"
        env = new_hook.pop("env", {})
        change_working_directory = new_hook.pop("change_working_directory", False)
        docker_version = init_global_docker_client().version()["Version"]
        quiet = True
        if Version(docker_version) < Version("19.03"):
            quiet = False
        remove_container = True
        if os.getenv("CONTENT_GITLAB_CI"):
            remove_container = False
        new_hook[
            "entry"
        ] = f'--entrypoint {new_hook.get("entry")} --network none {get_environment_flag(env)} {"--quiet" if quiet else ""} -u 4000:4000 {"--rm=false" if not remove_container else ""} {dev_image}'
        ret_hooks = []
        for (
            integration_script,
            files_with_objects,
        ) in object_to_files_with_objects.items():
            files = {file for file, _ in files_with_objects}
            hook = deepcopy(new_hook)
            if integration_script is not None:
                if config_arg:
                    args = deepcopy(self._get_property("args", []))
                    args.extend(
                        [
                            config_arg[0],
                            str(
                                (
                                    integration_script.path.parent / config_arg[1]
                                ).relative_to(CONTENT_PATH)
                            ),
                        ]
                    )
                    hook["args"] = args
                hook[
                    "id"
                ] = f"{hook['id']}-{integration_script.object_id}"  # for uniqueness
                hook[
                    "name"
                ] = f"{hook['name']}-{integration_script.object_id}"  # for uniqueness

                if support_pack_ignore_config and should_enable_network(
                    integration_script
                ):
                    hook["entry"] = hook["entry"].replace("--network none", "")
                    # We should isolate. We can run in the working directory of the integration/script and we can't use the `script_runner.py`
                    change_working_directory = True
                    if "script_runner" in hook["args"][0]:
                        hook["args"] = ["-m"] + hook["args"][1:-1]

                if change_working_directory:
                    hook[
                        "entry"
                    ] = f"-w {Path('/src') / integration_script.path.parent.relative_to(CONTENT_PATH)} {hook['entry']}"

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

    def _get_config_file_arg(self) -> Optional[Tuple]:
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

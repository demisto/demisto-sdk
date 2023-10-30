import functools
import os
import time
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Iterable, Optional, Tuple

from docker.errors import DockerException

from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.docker_helper import docker_login, get_docker
from demisto_sdk.commands.common.native_image import (
    NativeImageConfig,
    ScriptIntegrationSupportedNativeImages,
)
from demisto_sdk.commands.common.tools import get_yaml, logger
from demisto_sdk.commands.lint.linter import DockerImageFlagOption
from demisto_sdk.commands.pre_commit.hooks.hook import Hook


@functools.lru_cache
def get_docker_python_path() -> str:
    path_to_replace = str(Path(CONTENT_PATH))
    docker_path = [str(path).replace(path_to_replace, "/src") for path in PYTHONPATH]
    path = ":".join(sorted(docker_path))
    logger.debug(f"pythonpath in docker being set to {path}")
    return path


def with_native_tags(tags_to_files: dict, docker_image_flag: str) -> dict:
    docker_flags = set(docker_image_flag.split(","))
    all_tags_to_files = defaultdict(list)
    native_image_config = NativeImageConfig.get_instance()

    for image, scripts in tags_to_files.items():
        for file, yml in scripts:

            supported_native_images = ScriptIntegrationSupportedNativeImages(
                _id=yml.get("commonfields", {}).get("id", ""),
                native_image_config=native_image_config,
                docker_image=image,
            ).get_supported_native_docker_tags(docker_flags)
            for native_image in supported_native_images:
                all_tags_to_files[native_image].append((file, yml))
            if {
                DockerImageFlagOption.FROM_YML.value,
                DockerImageFlagOption.ALL_IMAGES.value,
            } & docker_flags:
                all_tags_to_files[image].append((file, yml))
    return all_tags_to_files


@functools.lru_cache
def get_yml_for_file(code_file) -> Optional[dict]:
    yml_in_directory = [f for f in os.listdir(code_file.parent) if f.endswith(".yml")]
    if (
        len(yml_in_directory) == 1
        and (yml_file := code_file.parent / yml_in_directory[0]).is_file()
    ):
        try:
            return get_yaml(yml_file)
        except Exception:
            logger.debug(f"Could not parse file {code_file}")
    return None
    # could be reasonable cant parse. We have some non-parsable ymls for tests


def docker_tag_to_runfiles(files_to_run: Iterable, docker_image_flag) -> dict:
    tags_to_files = defaultdict(list)
    for file in files_to_run:
        yml: Optional[dict] = get_yml_for_file(file)
        if not yml:
            continue
        for docker_image in docker_images_for_file(yml):
            tags_to_files[docker_image].append((file, yml))
    return with_native_tags(tags_to_files, docker_image_flag)


def docker_images_for_file(yml: dict) -> set:
    ret = set()
    if image := yml.get("dockerimage"):
        ret.add(image)
    script = yml.get("script", {})
    if isinstance(script, dict):
        image = script.get("dockerimage", "")
        if image:
            ret.add(image)
    if images := yml.get("alt_dockerimages"):
        ret.update(images)
    return ret


@functools.lru_cache(maxsize=256)
def devtest_image(image_tag, is_powershell):
    all_errors: list = []
    for _ in range(2):
        logger.info(f"getting devimage for {image_tag}, {is_powershell=}")
        return image_tag
        image, errors = get_docker().pull_or_create_test_image(
            image_tag, TYPE_PWSH if is_powershell else TYPE_PYTHON, push=docker_login()
        )
        if not errors:
            return image
        all_errors.append(errors)
    raise DockerException(all_errors)


def get_environment_flag() -> str:
    return f'--env "PYTHONPATH={get_docker_python_path()}"'


class DockerHook(Hook):
    def __int__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prepare_hook(self, files_to_run: Iterable):

        start_time = time.time()
        tag_to_files = docker_tag_to_runfiles(
            self.filter_files_matching_hook_config(files_to_run),
            self._get_property("docker_image", "from-yml"),
        )
        end_time = time.time()
        logger.info(
            f"Elapsed time to gather tags to files: {end_time - start_time} seconds"
        )
        start_time = time.time()

        for image, file_ymls in sorted(tag_to_files.items(), key=lambda item: item[0]):
            image_is_powershell = any(
                f[1].get("type") == "powershell" for f in file_ymls
            )
            dev_image = devtest_image(
                image, image_is_powershell
            )  # consider moving to before loop and threading.

            new_hook = {
                "id": f"{self._get_property('id')}-{image}",
                "name": f"{self._get_property('name')}-{image}",
                "language": "docker_image",
                "entry": f'--entrypoint {self._get_property("entry")} {get_environment_flag()} {dev_image}',
            }

            hooks = self._split_by_config_file(new_hook, file_ymls)
            for hook in hooks:
                self._set_properties(
                    hook, to_delete=["docker_image", "config_file_arg"]
                )

            self.hooks.extend(hooks)
        end_time = time.time()
        logger.info(
            f"DockerHook - Elapsed time to prep all the images: {end_time - start_time} seconds"
        )

    def _split_by_config_file(self, new_hook, file_ymls):
        folder_to_files = {}
        if config_arg := self._get_config_file_arg():

            folder_to_files = self._get_folder_to_ymls_by_config(
                file_ymls, config_arg[1]
            )
        else:
            folder_to_files = {None: [f[0] for f in file_ymls]}

        ret_hooks = []
        counter = 0
        for folder, files in folder_to_files.items():
            hook = deepcopy(new_hook)
            if folder is not None:
                args = deepcopy(self._get_property("args", []))
                args.extend(
                    [
                        config_arg[0],  # type:ignore
                        str(list(files)[0].parent / config_arg[1]),  # type:ignore
                    ]  # type:ignore
                )  # type:ignore
                hook["args"] = args
                hook["id"] = f"{hook['id']}-{counter}"
                hook["name"] = f"{hook['name']}-{counter}"
                counter += 1
            if self._set_files_on_hook(hook, files):
                ret_hooks.append(hook)
        return ret_hooks

    def _get_config_file_arg(self) -> Optional[Tuple]:
        if config_arg := self._get_property("config_file_arg"):
            arg_name = config_arg.get("arg_name")
            file_name = config_arg.get("file_name")
            if not arg_name or not file_name:
                raise ValueError(
                    "config_file_arg was provided in pre-commit configuration file"
                    " but not properly formed. Must have arg_name and file_name keys"
                )
            return arg_name, file_name
        return None

    def _get_folder_to_ymls_by_config(self, file_ymls, file_name):
        folder_to_files = defaultdict(set)

        for file, _ in file_ymls:
            if (file.parent / file_name).exists():
                folder_to_files[str(file.parent)].add(file)
            else:
                folder_to_files[None].add(file)  # type:ignore

        return folder_to_files

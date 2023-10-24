import functools
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Optional

from docker.errors import DockerException

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.docker_helper import get_docker
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
    all_tags_to_files = defaultdict(set)
    native_image_config = NativeImageConfig.get_instance()

    for image, scripts in tags_to_files.items():
        for file, yml in scripts:

            supported_native_images = ScriptIntegrationSupportedNativeImages(
                _id=yml.get("commonfields", {}).get("id", ""),
                native_image_config=native_image_config,
                docker_image=image,
            ).get_supported_native_docker_tags(docker_flags)
            for native_image in supported_native_images:
                all_tags_to_files[native_image].add(file)
            if {
                DockerImageFlagOption.FROM_YML.value,
                DockerImageFlagOption.ALL_IMAGES.value,
            } & docker_flags:
                all_tags_to_files[image].add(file)
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


def docker_tag_to_python_files(files_to_run: Iterable, docker_image_flag) -> dict:
    tags_to_files = defaultdict(list)
    for file in files_to_run:
        yml: Optional[dict] = get_yml_for_file(file)
        if not yml:
            continue
        if docker_image := docker_image_for_file(yml):
            tags_to_files[docker_image].append((file, yml))
    return with_native_tags(tags_to_files, docker_image_flag)


def docker_image_for_file(yml: dict) -> str:
    if image := yml.get("dockerimage"):
        return image
    script = yml.get("script", {})
    if isinstance(script, dict):
        return script.get("dockerimage", "")
    return ""


@functools.lru_cache
def devtest_image(param):
    image, errors = get_docker().pull_or_create_test_image(param)
    if errors:
        raise DockerException(errors)
    else:
        return image


def get_environment_flag() -> str:
    return f'--env "PYTHONPATH={get_docker_python_path()}"'


class GenericDocker(Hook):
    def __int__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prepare_hook(self, files_to_run: Iterable):

        all_hooks = []
        start_time = time.time()
        tag_to_files = docker_tag_to_python_files(
            self.files_to_matching_hook_config(files_to_run),
            self._get_property("docker_image", "from-yml"),
        )
        end_time = time.time()
        logger.info(f"Elapsed time: {end_time - start_time} seconds")
        for image, files in tag_to_files.items():
            dev_image = devtest_image(image)
            new_hook = {
                "id": f"{self._get_property('id')}-{image}",
                "name": f"{self._get_property('name')}-{image}",
                "language": "docker_image",
                "entry": f'--entrypoint {self._get_property("entry")} {get_environment_flag()} {dev_image}',
            }
            self._set_properties(new_hook, to_delete=["docker_image"])
            if self.set_files_on_hook(new_hook, files):
                all_hooks.append(new_hook)

        self.hooks.extend(all_hooks)

    def _set_properties(self, hook, to_delete=()):
        """
        Will alter the new hook, setting the properties that don't need unique behavior
        For any propery x, if x isn't already defined, x will be set according to the mode provided.

        For example, given an input

        args: 123
        args:nightly 456

        if the mode provided is nightly, args will be set to 456. Otherwise, the default (key with no :) will be taken

        Args:
            hook: the hook to modify
            to_delete: keys on the demisto config that we dont want to pass to precommit

        """
        for full_key in self.base_hook:
            key = full_key.split(":")[0]
            if hook.get(key) or key in to_delete:
                continue
            if prop := self._get_property(key):
                hook[key] = prop

    def _get_property(self, name, default=None):
        """
        Will get the given property from the base hook, taking mode into account
        Args:
            name: the key to get from the config
            default: the default value to return

        Returns: The value from the base hook
        """
        ret = None
        if self.mode:
            ret = self.base_hook.get(f"{name}:{self.mode.value}")
        return ret or self.base_hook.get(name, default)

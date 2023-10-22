import functools
import os
from collections import defaultdict
from copy import deepcopy
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

native_image_config = NativeImageConfig.get_instance()

@functools.cache
def get_docker_python_path() -> str:
    path_to_replace = str(Path(CONTENT_PATH))
    docker_path = [str(path).replace(path_to_replace, '/src') for path in PYTHONPATH]
    path = ":".join(sorted(docker_path))
    logger.debug(f'pythonpath in docker being set to {path}')
    return path


def with_native_tags(tags_to_files: dict[str, list], docker_image_flag: str) -> dict[str, set]:
    docker_flags = set(docker_image_flag.split(','))
    all_tags_to_files = defaultdict(set)
    for image, scripts in tags_to_files.items():
        for file, yml in scripts:

            supported_native_images = ScriptIntegrationSupportedNativeImages(
                _id=yml.get("commonfields", {}).get("id", ""),
                native_image_config=native_image_config,
                docker_image=image,
            ).get_supported_native_docker_tags(docker_flags)
            for native_image in supported_native_images:
                all_tags_to_files[native_image].add(file)
            if {DockerImageFlagOption.FROM_YML.value, DockerImageFlagOption.ALL_IMAGES.value} & docker_flags:
                all_tags_to_files[image].add(file)
    return all_tags_to_files
            
            
@functools.cache
def get_yml_for_file(code_file) -> Optional[dict]:
    yml_in_directory = [f for f in os.listdir(code_file.parent) if f.endswith(".yml")]
    if (
            len(yml_in_directory) == 1
            and (yml_file := code_file.parent / yml_in_directory[0]).is_file()
    ):
        try:
            return get_yaml(yml_file)
        except Exception:
            logger.debug(f'Could not parse file {code_file}')
    return None
            # could be reasonable cant parse. We have some non-parsable ymls for tests
            
def docker_tag_to_python_files(files_to_run: Iterable, docker_image_flag) -> dict[str, set]:
    tags_to_files = defaultdict(list)
    for file in files_to_run:
        yml: dict = get_yml_for_file(file)
        if not yml:
            continue
        if docker_image := docker_image_for_file(yml):
            tags_to_files[docker_image].append((file, yml))
    return with_native_tags(tags_to_files, docker_image_flag)


def docker_image_for_file(yml: dict) -> str:
    return yml.get("dockerimage") or yml.get("script", {}).get("dockerimage", "")



@functools.cache
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
        tag_to_files = docker_tag_to_python_files(files_to_run, self.base_hook.get('docker_image', 'from-yml'))
        for image, files in tag_to_files.items():
            dev_image = devtest_image(image)
            new_hook = deepcopy(self.base_hook)
            new_hook["id"] = f"{self.base_hook['id']}-{image}"
            new_hook["name"] = f"{self.base_hook['name']}-{image}"
            new_hook["language"] = "docker_image"
            new_hook.pop('docker-image', None)
            new_hook[
                "entry"
            ] = f'--entrypoint {self.base_hook["entry"]} {get_environment_flag()} {dev_image}'
            if self.set_files_on_hook(new_hook, files):
                all_hooks.append(new_hook)
        self.hooks.extend(all_hooks)

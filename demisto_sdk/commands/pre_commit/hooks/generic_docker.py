from collections import defaultdict
from typing import Iterable

import functools
import itertools
import os
from copy import deepcopy
from pathlib import Path

from docker.errors import DockerException

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.docker_helper import get_docker
from demisto_sdk.commands.common.tools import get_yaml, logger
from demisto_sdk.commands.pre_commit.hooks.hook import Hook


@functools.cache
def get_docker_python_path() -> str:
    path_to_replace = str(Path(CONTENT_PATH))
    docker_path = [str(path).replace(path_to_replace, '/src') for path in PYTHONPATH]
    path = ":".join(sorted(docker_path))
    logger.debug(f'pythonpath in docker being set to {path}')
    return path


def docker_tag_to_python_files(files_to_run: Iterable) -> dict:
    tags_to_files = defaultdict(set)
    for file in files_to_run:
        docker_image = docker_image_for_file(file)
        if docker_image:
            tags_to_files[devtest_image(docker_image)].add(file)
    return tags_to_files


@functools.cache
def docker_image_for_file(code_file) -> str:

    yml_in_directory = [f for f in os.listdir(code_file.parent) if f.endswith(".yml")]
    if (
            len(yml_in_directory) == 1
            and (yml_file := code_file.parent / yml_in_directory[0]).is_file()
    ):
        try:
            yml = get_yaml(yml_file)
            if not yml or not yml.get('type') or yml.get('type') == 'javascript':
                return ''
            return yml.get("dockerimage") or yml.get("script", {}).get("dockerimage", "")
        except Exception as e:
            logger.warning(f"Error parsing {yml_in_directory}, {yml_file}")
            return ""
    else:
        logger.debug(f"Yml file was not found for file {code_file}")
        return ""


@functools.cache
def devtest_image(param):
    image, errors = get_docker().pull_or_create_test_image(param)
    if errors:
        raise DockerException(errors)
    else:
        return image


@functools.cache  # precommit_env check this instead.
def get_python_path():  # TODO investigate what this is
    ":".join(str(path) for path in sorted(PYTHONPATH))


def get_environment_flag() -> str:
    return f'--env "PYTHONPATH={get_docker_python_path()}"'


class GenericDocker(Hook):

    def __int__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prepare_hook(self, files_to_run: Iterable):

        all_hooks = []
        tag_to_files: dict[str, list] = docker_tag_to_python_files(files_to_run)
        counter = 0  # added for uniqueness
        for tag, files in tag_to_files.items():
            counter = counter + 1
            new_hook = deepcopy(self.base_hook)
            new_hook["id"] = f"{self.base_hook['id']}-{counter}"
            new_hook["language"] = "docker_image"
            new_hook[
                "entry"
            ] = f'--entrypoint {self.base_hook["entry"]} {get_environment_flag()} {tag}'
            number_files_set = self.set_files_on_hook(new_hook, files)
            if number_files_set:
                all_hooks.append(new_hook)
        self.hooks.extend(all_hooks)

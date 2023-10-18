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



class GenericDocker(Hook):

    def __int__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def prepare_hook(self, python_version_to_files: dict):

        all_hooks = []
        tag_to_files: dict[str, list] = docker_tag_to_python_files(python_version_to_files)
        counter = 0  # added for uniqueness
        for tag, files in tag_to_files.items():
            counter = counter + 1
            new_hook = deepcopy(self.base_hook)
            new_hook["id"] = f"{self.base_hook['id']}-{counter}"
            new_hook["language"] = "docker_image"
            new_hook[
                "entry"
            ] = f'--entrypoint {self.base_hook["entry"]} --env "PYTHONPATH={get_docker_python_path()}" {tag} '
            number_files_set = self.set_files_on_hook(new_hook, files)
            if number_files_set:
                all_hooks.append(new_hook)
        self.hooks.extend(all_hooks)


def docker_tag_to_python_files(python_version_to_files: dict) -> dict:
    allfiles = set.union(*[x[1] for x in python_version_to_files.items()])
    return {
        devtest_image(image): list(group)
        for image, group in itertools.groupby(
            [file for file in allfiles if docker_image_for_file(file)],
            lambda f: docker_image_for_file(f),
        ) if image
    }


@functools.cache
def docker_image_for_file(code_file) -> str:

    yml_in_directory = [f for f in os.listdir(code_file.parent) if f.endswith(".yml")]
    if (
            len(yml_in_directory) == 1
            and (yml_file := code_file.parent / yml_in_directory[0]).is_file()
    ):

        yml = get_yaml(yml_file)
        return yml.get("dockerimage") or yml.get("script", {}).get("dockerimage", "")

    else:
        logger.debug(f"Yml file was not found for py file {code_file}")
        return ""


@functools.cache
def devtest_image(param):
    image, errors = get_docker().pull_or_create_test_image(param)
    if errors:
        raise DockerException(errors)
    else:
        return image


@functools.cache # precommit_env check this instead.
def get_python_path():  # TODO investigate what this is
    ":".join(str(path) for path in sorted(PYTHONPATH))

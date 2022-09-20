import pytest

from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
from demisto_sdk.commands.common.MDXServer import (DEMISTO_DEPS_DOCKER_NAME,
                                                   DockerMDXServer)
from demisto_sdk.commands.common.tests.readme_test import (
    MDX_SKIP_NPM_MESSAGE, README_INPUTS, assert_successful_mdx_call)
from demisto_sdk.commands.lint.docker_helper import init_global_docker_client


def container_is_up():
    return any(container.name == DEMISTO_DEPS_DOCKER_NAME
               for container in init_global_docker_client().containers.list())


def test_docker_server_up_and_down():
    with DockerMDXServer() as server:
        assert server.is_started()
        assert container_is_up()
        assert_successful_mdx_call()
    assert not container_is_up()


@pytest.mark.parametrize("current, answer", README_INPUTS)
def test_is_file_valid_docker_mdx_server(mocker, current, answer):
    readme_validator = ReadMeValidator(current)
    mocker.patch.object(ReadMeValidator, 'are_modules_installed_for_verify', return_value=False)
    assert readme_validator.is_valid_file() is answer


def test_docker_server_reentrant():
    with DockerMDXServer():
        with DockerMDXServer():
            assert container_is_up()
            assert_successful_mdx_call()
        assert_successful_mdx_call()
        assert container_is_up()
    assert not container_is_up()

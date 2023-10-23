import pytest

from demisto_sdk.commands.common.native_image import NativeImageConfig
from demisto_sdk.commands.pre_commit.hooks.generic_docker import GenericDocker
from demisto_sdk.commands.pre_commit.tests.pre_commit_test import create_hook


@pytest.fixture(autouse=True)
def native_image_config(mocker, repo) -> NativeImageConfig:
    native_image_config = NativeImageConfig.from_path(
        repo.docker_native_image_config.path
    )
    mocker.patch.object(
        NativeImageConfig, "get_instance", return_value=native_image_config
    )
    return native_image_config


def test_no_files(repo):
    """
    Given:
        no files supplied to the hook
    When:
        preparing hook
    Then:
        There are no raw hooks added to the config
    """
    raw_hook = create_hook({"args": []})
    GenericDocker(**raw_hook).prepare_hook([])

    hooks = raw_hook["repo"]["hooks"]
    assert len(hooks) == 0


def test_sanity_fail():
    assert False

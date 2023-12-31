from pathlib import Path

import pytest

from demisto_sdk.commands.common.native_image import NativeImageConfig
from demisto_sdk.commands.pre_commit.hooks.docker import (
    DockerHook,
    docker_tag_to_runfiles,
)
from demisto_sdk.commands.pre_commit.pre_commit_command import PreCommitContext
from demisto_sdk.commands.pre_commit.tests.pre_commit_test import Obj, create_hook


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
    DockerHook(**raw_hook).prepare_hook()

    hooks = raw_hook["repo"]["hooks"]
    assert len(hooks) == 0


@pytest.mark.parametrize(
    "mode, expected_text",
    [
        ("nightly", ["i am the nightly args"]),
        (None, ["i am some argument"]),
    ],
)
def test_moded_properties(mocker, mode, expected_text):
    """
    Given:
        The same config file
    When:
        Calling precommit with different modes

    Then:
        The value is properly returned

    """
    file_path = Path("SomeFile.py")
    file = (file_path, Obj())
    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.docker.docker_tag_to_runfiles",
        return_value={"sometag": [file]},
    )
    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.docker.devtest_image",
        return_value="devtestimg",
    )
    mocker.patch.object(
        PreCommitContext, "files_to_run_with_objects", [(file_path, None)]
    )
    mocker.patch.object(PreCommitContext, "dry_run", True)

    raw_hook = create_hook({"args": [], "language": "docker"}, mode=mode)

    raw_hook["hook"]["args"] = ["i am some argument"]
    raw_hook["hook"]["args:nightly"] = ["i am the nightly args"]
    raw_hook["hook"]["args:other"] = ["i am some other argument"]

    DockerHook(**raw_hook).prepare_hook()

    hook = raw_hook["repo"]["hooks"][0]
    assert hook["args"] == expected_text
    assert not any(arg for arg in hook if ":" in arg)


def test_get_property():
    """
    Given:
        A config file
    When:
        Calling on same config with different modes
    Then:
        The proper config is returned

    """
    nightly_val = "nightlyval"

    value1 = "value1"

    def assert_get_prop_successful(mode, prop, expected_value):
        assert (
            DockerHook(
                **create_hook(
                    {
                        "prop1": value1,
                        "prop1:nightly": nightly_val,
                        "prop1:othermode": "someval",
                    },
                    mode=mode,
                ),
            )._get_property(prop)
            == expected_value
        )

    assert_get_prop_successful("nightly", "prop1", nightly_val)
    assert_get_prop_successful(None, "prop1", value1)


def test_docker_tag_to_runfiles(mocker, native_image_config):
    mocked_responses = [
        Obj(
            object_id="id1",
            docker_image="demisto/python3:123.123.123.123",
            path=Path("file1.py"),
        ),
        Obj(object_id="id2", docker_image="image2", path=Path("file2.py")),
        Obj(
            object_id="id3",
            docker_image="demisto/python3:123.123.123.123",
            path=Path("file3.py"),
        ),
    ]
    native_latest_tag = "nativelatesttag"

    def set_mocks():
        mocker.patch(
            "demisto_sdk.commands.common.native_image.get_dev_native_image",
            return_value=native_latest_tag,
        )

    set_mocks()
    tag_to_files = docker_tag_to_runfiles(
        [(obj.path, obj) for obj in mocked_responses], "from-yml"
    )

    assert {
        f[0] for f in tag_to_files["demisto/python3:123.123.123.123"]
    } == {  # its ok this came back with duplicates
        Path("file3.py"),
        Path("file1.py"),
    }
    assert tag_to_files["image2"][0] == (
        Path("file2.py"),
        mocked_responses[1],
    )

    tag_to_files = docker_tag_to_runfiles(
        [(obj.path, obj) for obj in mocked_responses], "native:dev,from-yml"
    )
    assert len(tag_to_files) == 3
    assert native_latest_tag in tag_to_files


def test__set_properties():
    """
    Given:
        A config file
    When:
        Calling on same config with different modes
    Then:
        The proper config is in base_hook.
    """
    nightly_val = "nightlyval"

    value1 = "value1"

    def assert_get_prop_successful(mode, expected_value):
        hook = create_hook(
            {
                "prop1": value1,
                "prop1:nightly": nightly_val,
                "prop1:othermode": "someval",
                "other_prop": "whatever",
                "nonused:mode": "isignored",
            },
            mode=mode,
        )
        docker_hook = DockerHook(**hook)
        assert docker_hook.base_hook == expected_value

    assert_get_prop_successful(
        "nightly",
        {"prop1": nightly_val, "other_prop": "whatever"},
    )
    assert_get_prop_successful(None, {"prop1": value1, "other_prop": "whatever"})

from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import PreCommitModes
from demisto_sdk.commands.common.native_image import NativeImageConfig
from demisto_sdk.commands.pre_commit.hooks.docker import (
    DockerHook,
    docker_tag_to_runfiles,
)
from demisto_sdk.commands.pre_commit.tests.pre_commit_test import create_hook


def assert_lists_have_same_elements(list1, list2):
    assert len(list1) == len(list2), "Lists have different lengths"
    for item1 in list1:
        if item1 not in list2:
            assert False, "Lists do not have the same elements"


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
    DockerHook(**raw_hook).prepare_hook([])

    hooks = raw_hook["repo"]["hooks"]
    assert len(hooks) == 0


@pytest.mark.parametrize(
    "mode, expected_text",
    [
        (PreCommitModes.NIGHTLY, ["i am the nightly args"]),
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
    file = (file_path, {"commonfields": {"id": "id1"}})
    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.docker.docker_tag_to_runfiles",
        return_value={"sometag": [file]},
    )
    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.docker.devtest_image",
        return_value="devtestimg",
    )
    raw_hook = create_hook({"args": []})

    raw_hook["hook"]["args"] = ["i am some argument"]
    raw_hook["hook"]["args:nightly"] = ["i am the nightly args"]
    raw_hook["hook"]["args:other"] = ["i am some other argument"]

    DockerHook(**raw_hook, mode=mode).prepare_hook([file_path])

    hook = raw_hook["repo"]["hooks"][0]
    assert hook["args"] == expected_text
    assert not any(arg for arg in hook if ":" in arg)


def test_get_property():
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
                    }
                ),
                mode=mode
            )._get_property(prop)
            == expected_value
        )

    assert_get_prop_successful(PreCommitModes.NIGHTLY, "prop1", nightly_val)
    assert_get_prop_successful(None, "prop1", value1)


def test_docker_tag_to_runfiles(mocker, native_image_config):
    mocked_responses = [
        {
            "yml": {"commonfields": {"id": "id1"}},
            "docker_image": "demisto/python3:123.123.123.123",
            "path": Path("file1.py"),
        },
        {
            "yml": {"commonfields": {"id": "id2"}},
            "docker_image": "image2",
            "path": Path("file2.py"),
        },
        {
            "yml": {"commonfields": {"id": "id3"}},
            "docker_image": "demisto/python3:123.123.123.123",
            "path": Path("file3.py"),
        },
        {
            "yml": {"commonfields": {"id": "id4"}},
            "docker_image": None,
            "path": Path("file4.md"),
        },
    ]
    native_latest_tag = "nativelatesttag"

    def set_mocks():
        def mock_yml_for_file(x):
            return [res.get("yml") for res in mocked_responses if res.get("path") == x][
                0
            ]

        def mock_docker_for_file(x):
            return [
                res.get("docker_image")
                for res in mocked_responses
                if res.get("yml") == x
            ][0]

        mocker.patch(
            "demisto_sdk.commands.pre_commit.hooks.docker.get_yml_for_file",
            side_effect=mock_yml_for_file,
        )
        mocker.patch(
            "demisto_sdk.commands.pre_commit.hooks.docker.docker_image_for_file",
            side_effect=mock_docker_for_file,
        )
        mocker.patch(
            "demisto_sdk.commands.common.native_image.get_dev_native_image",
            return_value=native_latest_tag,
        )

    set_mocks()
    tag_to_files = docker_tag_to_runfiles(
        [r.get("path") for r in mocked_responses], "from-yml"
    )

    assert {
        f[0] for f in tag_to_files["demisto/python3:123.123.123.123"]
    } == {  # its ok this came back with duplicates
        Path("file3.py"),
        Path("file1.py"),
    }
    assert tag_to_files["image2"][0] == (
        Path("file2.py"),
        {"commonfields": {"id": "id2"}},
    )

    set_mocks()
    tag_to_files = docker_tag_to_runfiles(
        [r.get("path") for r in mocked_responses], "native:dev,from-yml"
    )
    assert len(tag_to_files) == 3
    assert native_latest_tag in tag_to_files

from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import PreCommitModes
from demisto_sdk.commands.common.native_image import NativeImageConfig
from demisto_sdk.commands.pre_commit.hooks.generic_docker import (
    GenericDocker,
    docker_tag_to_python_files,
)
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
    file = Path("SomeFile.py")
    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.generic_docker.docker_tag_to_python_files",
        return_value={"sometag": [file]},
    )
    mocker.patch(
        "demisto_sdk.commands.pre_commit.hooks.generic_docker.devtest_image",
        return_value="devtestimg",
    )
    raw_hook = create_hook({"args": []})

    raw_hook["hook"]["args"] = ["i am some argument"]
    raw_hook["hook"]["args:nightly"] = ["i am the nightly args"]
    raw_hook["hook"]["args:other"] = ["i am some other argument"]

    GenericDocker(**raw_hook, mode=mode).prepare_hook([file])

    hook = raw_hook["repo"]["hooks"][0]
    assert hook["args"] == expected_text
    assert not any(arg for arg in hook if ":" in arg)


def test_get_property():
    nightly_val = "nightlyval"

    value1 = "value1"

    def assert_get_prop_successful(mode, prop, expected_value):
        assert (
            GenericDocker(
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


def test_docker_tag_to_python_files(mocker, native_image_config):
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
            "yml": {"commonfields": {"id": "id1"}},
            "docker_image": None,
            "path": Path("file4.md"),
        },
    ]
    native_latest_tag = "nativelatesttag"

    def set_mocks():
        mocker.patch(
            "demisto_sdk.commands.pre_commit.hooks.generic_docker.get_yml_for_file",
            side_effect=[r.get("yml") for r in mocked_responses],
        )
        mocker.patch(
            "demisto_sdk.commands.pre_commit.hooks.generic_docker.docker_image_for_file",
            side_effect=[r.get("docker_image") for r in mocked_responses],
        )
        mocker.patch(
            "demisto_sdk.commands.common.native_image.get_dev_native_image",
            return_value=native_latest_tag,
        )

    set_mocks()
    tag_to_files = docker_tag_to_python_files(
        [r.get("path") for r in mocked_responses], "from-yml"
    )

    assert len(tag_to_files) == 2
    assert tag_to_files["demisto/python3:123.123.123.123"] == {
        Path("file3.py"),
        Path("file1.py"),
    }
    assert tag_to_files["image2"] == {Path("file2.py")}

    set_mocks()
    tag_to_files = docker_tag_to_python_files(
        [r.get("path") for r in mocked_responses], "native:dev,from-yml"
    )
    assert len(tag_to_files) == 3
    assert native_latest_tag in tag_to_files

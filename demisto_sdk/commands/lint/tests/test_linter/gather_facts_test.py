import shutil
import tempfile
from typing import Callable

import pytest
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.lint import linter
from TestSuite.test_tools import ChangeCWD


def initiate_linter(
    demisto_content, integration_path, docker_engine=False, docker_image_flag="from-yml"
):
    return linter.Linter(
        content_repo=demisto_content,
        pack_dir=Path(integration_path),
        req_2=[],
        req_3=[],
        docker_engine=docker_engine,
        docker_timeout=60,
        docker_image_flag=docker_image_flag,
    )


class TestYamlParse:
    def test_valid_yaml_key_script_is_dict(
        self, demisto_content, create_integration: Callable, mocker
    ):
        integration_path: Path = create_integration(
            content_path=demisto_content, type_script_key=True
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})

    def test_valid_yaml_key_script_is_not_dict(
        self, demisto_content: Callable, create_integration: Callable, mocker
    ):
        integration_path: Path = create_integration(
            content_path=demisto_content, type_script_key=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})

    def test_not_valid_yaml(
        self, demisto_content: Callable, create_integration: Callable
    ):
        integration_path: Path = create_integration(
            content_path=demisto_content, yml=True
        )
        runner = initiate_linter(demisto_content, integration_path)
        assert runner._gather_facts(modules={})

    def test_checks_common_server_python(self, repo):
        """
        Given
        - Repo with CommonServerPython script
        When
        - Running lint on a repo with a change to CommonServerPython
        Then
        - Validate that the CommonServerPython is in the file list to check
        """
        pack = repo.create_pack("Base")
        script = pack.create_script("CommonServerPython")
        script.create_default_script()
        script_path = Path(script.path)
        runner = initiate_linter(pack.path, script_path)
        runner._gather_facts(modules={})
        common_server_python_path = runner._facts.get("lint_files")[0]
        assert "Packs/Base/Scripts/CommonServerPython/CommonServerPython.py" in str(
            common_server_python_path
        )


class TestPythonPack:
    def test_package_is_python_pack(
        self, demisto_content: Callable, create_integration: Callable, mocker
    ):
        integration_path: Path = create_integration(
            content_path=demisto_content, js_type=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})

    def test_package_is_not_python_pack(
        self, demisto_content: Callable, create_integration: Callable
    ):
        integration_path: Path = create_integration(
            content_path=demisto_content, js_type=True
        )
        runner = initiate_linter(demisto_content, integration_path)
        assert runner._gather_facts(modules={})


class TestDockerImagesCollection:
    def test_docker_images_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        exp_image = "test-image:12.0"
        exp_py_num = "2.7"
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, image=exp_image, image_py_num=exp_py_num
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})

        assert runner._facts["images"][0][0] == exp_image
        assert runner._facts["images"][0][1] == exp_py_num

    def test_docker_images_not_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        exp_image = "demisto/python:1.3-alpine"
        exp_py_num = "2.7"
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, image="", image_py_num=exp_py_num
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})

        assert runner._facts["images"][0][0] == exp_image
        assert runner._facts["images"][0][1] == exp_py_num

    @pytest.mark.parametrize(
        argnames="docker_image_flag, exp_images ",
        argvalues=[
            ("native:ga", "demisto/py3-native:8.2.0.12345"),
            ("native:maintenance", "demisto/py3-native:8.1.0.12345"),
            ("native:dev", "demisto/py3-native:8.3.0.12345"),
            ("from-yml", "demisto/py3-tools:1.0.0.42258"),
            (
                "all",
                [
                    "demisto/py3-tools:1.0.0.42258",
                    "demisto/py3-native:8.1.0.12345",
                    "demisto/py3-native:8.2.0.12345",
                    "demisto/py3-native:8.3.0.12345",
                ],
            ),
        ],
    )
    def test_docker_images_according_to_docker_image_flag(
        self, mocker, pack, docker_image_flag, exp_images
    ):
        """
        Given
            - An integration to run lint on, and a docker image flag:
                1. docker image flag = "native:ga"
                2. docker image flag = "native:maintenance"
                3. docker image flag = "native:dev"
                4. docker image flag = "from-yml"
                5. docker image flag = "all"
        When
            - running the linter.
        Then
            - Ensure that the docker images that lint will run on are as expected:
                1. The native ga image that is defined in the native configuration file
                2. The native maintenance image that is defined in the native configuration file
                3. The latest tag of the native image from Docker Hub (mocked tag).
                4. The docker image that is defined in the integration's yml file.
                5. All 4 images from tests: 1-4.
        """
        mocker.patch(
            "demisto_sdk.commands.lint.helpers.get_python_version_from_image",
            return_value="3.7",
        )
        # TODO: need to mock this function because it throws errors
        native_image_latest_tag = "8.3.0.12345"
        mocker.patch.object(
            DockerImageValidator,
            "get_docker_image_latest_tag_request",
            return_value=native_image_latest_tag,
        )

        integration_name = "TestIntegration"
        docker_image_yml = "demisto/py3-tools:1.0.0.42258"
        integration_yml = {
            "commonfields": {"id": integration_name, "version": -1},
            "name": integration_name,
            "display": integration_name,
            "description": f"this is an integration {integration_name}",
            "category": "category",
            "script": {
                "type": "python",
                "subtype": "python3",
                "script": "",
                "commands": [],
                "dockerimage": docker_image_yml,
            },
        }
        test_integration = pack.create_integration(
            name=integration_name, yml=integration_yml
        )

        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
            )
            runner._gather_facts(modules={})

        actual_image = runner._facts["images"]
        if len(actual_image) == 1:
            assert actual_image[0][0] == exp_images
        else:  # more than one image (all option)
            images = []
            for img in actual_image:
                images.append(img[0])
            assert images == exp_images

    # def test_get_versioned_native_image(self, mocker, demisto_content: Callable, create_integration: Callable,
    #                                     native_image_config):
    #
    #     mocker.patch.object(linter.Linter, "_docker_login")
    #     mocker.patch.object(linter.Linter, "_update_support_level")
    #     mocker.patch.object(NativeImageConfig, "__init__", return_value=None)
    #     linter.Linter._docker_login.return_value = False
    #     integration_path: Path = create_integration(
    #         content_path=demisto_content, image="test-image:12.0", image_py_num="3.10"
    #     )
    #     linter_obj = initiate_linter(demisto_content, integration_path, True)
    #     native_image = native_image_config.flags_versions_mapping.get('native:ga')
    #
    #     versioned_native_image = linter_obj._get_versioned_native_image(native_image)
    #     print(versioned_native_image)


class TestTestsCollection:
    def test_tests_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, no_tests=False
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert runner._facts["test"]

    def test_tests_not_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, no_tests=True
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["test"]


class TestLintFilesCollection:
    def test_lint_files_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, no_lint_file=False
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert (
            runner._facts["lint_files"][0]
            == integration_path / f"{integration_path.name}.py"
        )
        assert (
            runner._facts["lint_unittest_files"][0]
            == integration_path / f"{integration_path.name}_test.py"
        )

    def test_lint_files_not_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, no_lint_file=True
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["lint_files"]


class TestTestRequirementsCollection:
    def test_test_requirements_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")
        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(
            content_path=demisto_content, test_reqs=True
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert runner._facts["additional_requirements"]
        test_requirements = ["mock", "pre-commit", "pytest"]
        for test_req in test_requirements:
            assert test_req in runner._facts["additional_requirements"]

    def test_test_requirements_not_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch.object(linter.Linter, "_docker_login")
        mocker.patch.object(linter.Linter, "_update_support_level")

        linter.Linter._docker_login.return_value = False
        integration_path: Path = create_integration(content_path=demisto_content)
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["additional_requirements"]


files_strings = [
    "/Users/user/dev/demisto/content/Packs/EDL/Integrations/EDL/EDL_test.py",
    "/Users/user/dev/demisto/content/Packs/EDL/Integrations/EDL/EDL.py",
    "/Users/user/dev/demisto/content/Packs/EDL/Integrations/EDL/NGINXApiModule.py",
]
files_paths = [Path(i) for i in files_strings]


def test_remove_gitignore_files(mocker, demisto_content):
    """
    Given:
    - Linter module with files to ignore.

    When:
    - Calling _remove_gitignore_files method.

    Then:
    - Remove the ignored files from self._facts['lint_files'].

    """

    class GitMock:
        def ignored(self, files):
            return files[-1:]

    mocker.patch("git.Repo", return_value=GitMock())
    runner = initiate_linter(demisto_content, "")
    runner._facts["lint_files"] = files_paths
    assert files_paths[-1] in runner._facts["lint_files"]
    runner._remove_gitignore_files("prompt")
    assert files_paths[-1] not in runner._facts["lint_files"]


def test_linter_pack_abs_dir():
    from demisto_sdk.commands.lint.linter import Linter

    dir_path = tempfile.mkdtemp()
    python_path = f"{dir_path}/__init__.py"
    expected_path = dir_path
    path_list = [python_path, dir_path]

    for path in path_list:
        linter_instance: Linter = Linter(
            pack_dir=Path(path),
            content_repo=Path(path),
            req_3=[],
            req_2=[],
            docker_engine=False,
            docker_timeout=30,
        )

        assert linter_instance._pack_abs_dir == Path(expected_path)

        # Delete the temporary directory we created
        if Path(path).is_dir():
            shutil.rmtree(Path(path))

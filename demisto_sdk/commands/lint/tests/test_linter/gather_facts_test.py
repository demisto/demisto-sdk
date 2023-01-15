import logging
import shutil
import tempfile
from typing import Callable

import pytest
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.lint import linter
from TestSuite.test_tools import ChangeCWD

logger = logging.getLogger("demisto-sdk")


def initiate_linter(
    demisto_content,
    integration_path,
    docker_engine=False,
    docker_image_flag=linter.DockerImageFlagOption.FROM_YML.value,
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
            (
                linter.DockerImageFlagOption.NATIVE_GA.value,
                "demisto/py3-native:8.2.0.12345",
            ),
            (
                linter.DockerImageFlagOption.NATIVE_MAINTENANCE.value,
                "demisto/py3-native:8.1.0.12345",
            ),
            (
                linter.DockerImageFlagOption.NATIVE_DEV.value,
                "demisto/py3-native:8.3.0.12345",
            ),
            (
                linter.DockerImageFlagOption.FROM_YML.value,
                "demisto/py3-tools:1.0.0.42258",
            ),
            (
                linter.DockerImageFlagOption.ALL_IMAGES.value,
                [
                    "demisto/py3-tools:1.0.0.42258",
                    "demisto/py3-native:8.1.0.12345",
                    "demisto/py3-native:8.2.0.12345",
                    "demisto/py3-native:8.3.0.12345",
                ],
            ),
            ("demisto/py3-tools:1.0.0.40800", "demisto/py3-tools:1.0.0.40800"),
        ],
    )
    def test_docker_images_according_to_docker_image_flag(
        self, mocker, pack, docker_image_flag, exp_images
    ):
        """
        This test checks that the docker images to run lint on determined according to the docker image flag.

        Given
            - An integration to run lint on, and a docker image flag:
                1. Docker image flag = "native:ga"
                2. Docker image flag = "native:maintenance"
                3. Docker image flag = "native:dev"
                4. Docker image flag = "from-yml"
                5. Docker image flag = "all"
                6. Docker image flag = a specific docker image from Docker Hub (demisto/py3-tools:1.0.0.40800)
        When
            - running the linter.
        Then
            - Ensure that the docker images that lint will run on are as expected:
                1. The native ga image that is defined in the native configuration file
                2. The native maintenance image that is defined in the native configuration file
                3. The latest tag of the native image from Docker Hub (mocked tag).
                4. The docker image that is defined in the integration's yml file.
                5. All 4 images from tests: 1-4.
                6. The specific docker image form docker hub that was set as the flag (demisto/py3-tools:1.0.0.40800).
        """
        # Mock:
        native_image_latest_tag = "8.3.0.12345"
        mocker.patch.object(
            DockerImageValidator,
            "get_docker_image_latest_tag_request",
            return_value=native_image_latest_tag,
        )
        mocker.patch.object(linter, "get_python_version_from_image", return_value="3.8")

        # Crete integration to test on:
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

        # Run lint:
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        actual_image = runner._facts["images"]
        if len(actual_image) == 1:
            assert actual_image[0][0] == exp_images
        else:  # more than one image ('all' flag)
            images = []
            for img in actual_image:
                images.append(img[0])
            assert images == exp_images

    @pytest.mark.parametrize(
        argnames="docker_image_flag, exp_versioned_native_image_name",
        argvalues=[
            (linter.DockerImageFlagOption.NATIVE_GA.value, "native:8.2"),
            (linter.DockerImageFlagOption.NATIVE_MAINTENANCE.value, "native:8.1"),
            (linter.DockerImageFlagOption.NATIVE_DEV.value, "native:dev"),
        ],
    )
    def test_docker_images_key_not_exists_in_yml(
        self, mocker, pack, docker_image_flag, exp_versioned_native_image_name
    ):
        """
        This test checks that for integration that doesn't have the 'dockerimage' key in it's YML, if a native image
        flag was given the test on docker and in host are skipped.

        Given
            - An integration to run lint on (integration tml doesn't have a 'dockerimage' key), and a docker image flag:
                1. Docker image flag = "native:ga"
                2. Docker image flag = "native:maintenance"
                3. Docker image flag = "native:dev"
        When
            - running the linter.
        Then
            - Ensure that the docker images list is empty, and suitable logs (skipping) were written.
        """
        # Mock:
        mocker.patch.object(linter, "get_python_version_from_image", return_value="3.8")
        log = mocker.patch.object(logger, "info")

        # Crete integration to test on:
        integration_name = "TestIntegration"
        test_integration = pack.create_integration(name=integration_name)

        # Run lint:
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        assert runner._facts["images"] == []
        assert (
            f"Skipping checks on docker for {exp_versioned_native_image_name} - TestIntegration is not supported"
            f" by the requested native image: {exp_versioned_native_image_name}"
            in log.call_args_list[-2][0][0]
        )
        assert (
            f"{integration_name} - Facts - No docker images to run on - "
            f"Skipping run lint in host as well." in log.call_args_list[-1][0][0]
        )

    def test_invalid_docker_image_as_docker_image_flag(self, mocker, pack):
        """
        This test checks that if an invalid docker image was given as the docker image flag, the linter will try to
        run the unit test on it and will write suitable logs.

        Given
            - An invalid docker image (for example a docker image that doesn't exist in Docker Hub).
        When
            - running the linter.
        Then
            - Ensure that a suitable log was written.
        """
        # Mock:
        log_error = mocker.patch.object(logger, "error")

        # Crete integration to test on:
        integration_name = "TestIntegration"
        test_integration = pack.create_integration(name=integration_name)

        # Run lint:
        invalid_docker_image = "demisto/blabla:1.0.0.40800"
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=invalid_docker_image,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        assert runner._facts["images"][0][0] == invalid_docker_image
        assert (
            f"Get python version from image {invalid_docker_image} - Failed detecting Python version for image"
            f" {invalid_docker_image}" in log_error.call_args_list[0][0][0]
        )

    @pytest.mark.parametrize(
        argnames="docker_image_flag, exp_versioned_native_image_name",
        argvalues=[
            (linter.DockerImageFlagOption.NATIVE_GA.value, "native:8.2"),
            (linter.DockerImageFlagOption.NATIVE_MAINTENANCE.value, "native:8.1"),
            (linter.DockerImageFlagOption.NATIVE_DEV.value, "native:dev"),
            (linter.DockerImageFlagOption.ALL_IMAGES.value, "native:dev"),
        ],
    )
    def test_integration_not_supported_by_requested_native_image(
        self, mocker, pack, docker_image_flag, exp_versioned_native_image_name
    ):
        """
        This test checks that if a docker image flag of a native image was given (native:ga, native:maintenance,
        native:dev) and the integration is supported by the requested native image, the linter tests on docker and in
        host will be skipped, and suitable logs will be written.

        Given
            - An integration (with a docker image that is not supported by the native image) to run lint on,
              and a docker image flag:
                1. Docker image flag = "native:ga"
                2. Docker image flag = "native:maintenance"
                3. Docker image flag = "native:dev"
                4. Docker image flag = "all"
        When
            - running the linter.
        Then
            -
                1-3. Ensure that the docker images list is empty, and suitable logs (skipping) were written.
                4. Ensure that the docker image is only the docker image from the integration yml.
        """
        # Mock:
        mocker.patch.object(linter, "get_python_version_from_image", return_value="3.8")
        log = mocker.patch.object(logger, "info")

        # Crete integration to test on:
        integration_name = "TestIntegration"
        # this docker image is not supported by the native images (in the native docker config file)
        docker_image_yml = "demisto/pyjwt:1.0"
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

        # Run lint:
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        docker_images = runner._facts["images"]
        if docker_image_flag == linter.DockerImageFlagOption.ALL_IMAGES.value:
            assert len(docker_images) == 1
            assert docker_images[0][0] == docker_image_yml
        else:
            assert len(docker_images) == 0
            assert (
                f"Skipping checks on docker for {exp_versioned_native_image_name} - TestIntegration is not supported"
                f" by the requested native image: {exp_versioned_native_image_name}"
                in log.call_args_list[-2][0][0]
            )
            assert (
                f"{integration_name} - Facts - No docker images to run on - "
                f"Skipping run lint in host as well." in log.call_args_list[-1][0][0]
            )

    def test_wrong_native_docker_image_flag(self, mocker, pack):
        """
        This test checks that if a native docker image flag with a wrong suffix was given, a suitable
        exception is raised.

        Given
            - An integration to run lint on, and a docker image flag with a native prefix and a wring suffix.
             (suffix is not one of the following: ga, maintenance or dev).
        When
            - running the linter.
        Then
            - Ensure that the a suitable exception is raised.
        """
        # Mock:
        log = mocker.patch.object(logger, "error")

        # Crete integration to test on:
        integration_name = "TestIntegration"
        test_integration = pack.create_integration(name=integration_name)

        # Run lint:
        docker_image_flag = "native:wrong_suffix"
        with pytest.raises(Exception) as e:
            with ChangeCWD(pack.repo_path):
                runner = initiate_linter(
                    pack.repo_path,
                    test_integration.path,
                    True,
                    docker_image_flag=docker_image_flag,
                )
                runner._gather_facts(modules={})

        # Verify docker images:
        expected_err_msg = (
            f"The requested native image: '{docker_image_flag}' is not supported. "
            f"The possible options are: 'native:ga', 'native:maintenance' and 'native:dev'. "
            f"For supported native image versions please see: 'Tests/docker_native_image_config.json'"
        )
        assert runner._facts["images"] == []
        assert str(e.value) == expected_err_msg
        assert (
            log.call_args_list[0][0][0]
            == f"Skipping checks on docker for '{docker_image_flag}' - {expected_err_msg}"
        )

    def test_docker_image_flag_version_not_exists_in_native_config_file(
        self, mocker, pack
    ):
        """
        This test checks that if a native docker image flag was given, and the flag doesn't have a mapped native
        version name in the docker config file, the linter tests on docker and in host will be skipped,
         and suitable logs will be written.

        Given
            - An integration to run lint on, and a native docker image flag that doesn't have a mapped native image
              version in the config file.
        When
            - running the linter.
        Then
            - Ensure that the docker images list is empty, and that a suitable log message (skipping) was written.
        """
        # Mock:
        native_image_config_mock = {
            "native_images": {
                "native:8.1": {
                    "supported_docker_images": [
                        "python3",
                        "py3-tools",
                        "unzip",
                        "chromium",
                        "tesseract",
                        "tld",
                    ],
                    "docker_ref": "demisto/py3-native:8.1.0.12345",
                }
            },
            "ignored_content_items": [
                {
                    "id": "UnzipFile",
                    "reason": "this is just a test",
                    "ignored_native_images": ["native:8.1"],
                },
            ],
            "flags_versions_mapping": {
                "native:dev": "native:dev",
                "native:ga": "native:8.2",
                "native:maintenance": "",
            },
        }

        mocker.patch.object(linter, "get_python_version_from_image", return_value="3.8")
        mocker.patch(
            "demisto_sdk.commands.common.native_image.NativeImageConfig.load",
            return_value=native_image_config_mock,
        )
        log = mocker.patch.object(logger, "info")

        # Crete integration to test on:
        integration_name = "TestIntegration"
        test_integration = pack.create_integration(name=integration_name)

        # Run lint:
        docker_image_flag = "native:maintenance"
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        assert runner._facts["images"] == []
        assert (
            f"Skipping checks on docker for '{docker_image_flag}' - The requested native image:"
            f" '{docker_image_flag}' is not supported. For supported native image versions please see:"
            f" 'Tests/docker_native_image_config.json'" in log.call_args_list[-2][0][0]
        )
        assert (
            f"{integration_name} - Facts - No docker images to run on - "
            f"Skipping run lint in host as well." in log.call_args_list[-1][0][0]
        )


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

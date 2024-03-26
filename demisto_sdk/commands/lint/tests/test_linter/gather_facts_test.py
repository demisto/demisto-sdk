import shutil
import tempfile
from typing import Callable

import pytest
from packaging.version import Version
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.hook_validations.docker import DockerImageValidator
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.lint import linter
from TestSuite.pack import Pack
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list


def initiate_linter(
    demisto_content,
    integration_path,
    docker_engine=False,
    docker_image_flag=linter.DockerImageFlagOption.FROM_YML.value,
    all_packs=False,
    docker_image_target="",
):
    return linter.Linter(
        content_repo=demisto_content,
        pack_dir=Path(integration_path),
        docker_engine=docker_engine,
        docker_timeout=60,
        docker_image_flag=docker_image_flag,
        all_packs=all_packs,
        docker_image_target=docker_image_target,
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
        runner = initiate_linter(Path(pack.path), script_path)
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
            content_path=demisto_content, js_type=False, api_module=True
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        runner = initiate_linter(demisto_content, integration_path)
        assert not runner._gather_facts(modules={})
        assert len(runner._facts["lint_files"]) == 1
        assert "Sample_integration.py" == runner._facts["lint_files"][0].name

    def test_package_is_python_pack_api_module_script(
        self, demisto_content, pack, mocker
    ):
        from demisto_sdk.commands.common.git_util import Repo

        script = pack.create_script(name="TestApiModule")
        mocker.patch.object(Repo, "ignored", return_value=[])
        mocker.patch.object(linter.Linter, "_update_support_level")
        runner = initiate_linter(demisto_content, script.path)
        assert not runner._gather_facts(modules={})
        assert len(runner._facts["lint_files"]) == 1
        assert "TestApiModule.py" == runner._facts["lint_files"][0].name

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
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
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
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        integration_path: Path = create_integration(
            content_path=demisto_content, image="", image_py_num=exp_py_num
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})

        assert runner._facts["images"][0][0] == exp_image
        assert runner._facts["images"][0][1] == exp_py_num

    @pytest.mark.parametrize(
        argnames="docker_image_flag, exp_images, native_target_img ",
        argvalues=[
            (
                linter.DockerImageFlagOption.NATIVE_GA.value,
                "demisto/py3-native:8.2.0.12345",
                "",
            ),
            (
                linter.DockerImageFlagOption.NATIVE_MAINTENANCE.value,
                "demisto/py3-native:8.1.0.12345",
                "",
            ),
            (
                linter.DockerImageFlagOption.NATIVE_DEV.value,
                "demisto/py3-native:8.3.0.12345",
                "",
            ),
            (
                linter.DockerImageFlagOption.FROM_YML.value,
                "demisto/py3-tools:1.0.0.42258",
                "",
            ),
            (
                linter.DockerImageFlagOption.NATIVE_CANDIDATE.value,
                "demisto/py3-native:8.2.1.12345",
                "",
            ),
            (
                linter.DockerImageFlagOption.ALL_IMAGES.value,
                [
                    "demisto/py3-tools:1.0.0.42258",
                    "demisto/py3-native:8.1.0.12345",
                    "demisto/py3-native:8.2.0.12345",
                    "demisto/py3-native:8.2.1.12345",
                ],
                "",
            ),
            ("demisto/py3-tools:1.0.0.40800", "demisto/py3-tools:1.0.0.40800", ""),
            (
                linter.DockerImageFlagOption.NATIVE_TARGET.value,
                "demisto/py3-tools:1.0.0.40800",
                "demisto/py3-tools:1.0.0.40800",
            ),
        ],
    )
    def test_docker_images_according_to_docker_image_flag(
        self, mocker, pack, docker_image_flag, exp_images, native_target_img
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
                7. Docker image flag = "native:target", Docker target = a specific docker image from Docker Hub
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
                7. The specific docker image form docker hub that was set as the flag (demisto/py3-tools:1.0.0.40800).
        """
        # Mock:
        native_image_latest_tag = "8.3.0.12345"
        mocker.patch.object(
            DockerImageValidator,
            "get_docker_image_latest_tag_request",
            return_value=native_image_latest_tag,
        )
        mocker.patch.object(linter, "get_python_version", return_value=Version("3.8"))

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
                Path(pack.repo_path),
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
                docker_image_target=native_target_img,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        actual_image = runner._facts["images"]
        if len(actual_image) == 1:
            assert actual_image[0][0] == exp_images
        else:  # more than one image ('all' flag)
            for img in actual_image:
                assert img[0] in exp_images
            assert len(actual_image) == len(exp_images)

    @pytest.mark.parametrize(
        argnames="docker_image_flag, exp_versioned_native_image_name",
        argvalues=[
            (linter.DockerImageFlagOption.NATIVE_GA.value, "native:8.2"),
            (linter.DockerImageFlagOption.NATIVE_MAINTENANCE.value, "native:8.1"),
            (linter.DockerImageFlagOption.NATIVE_DEV.value, "native:dev"),
            (linter.DockerImageFlagOption.NATIVE_TARGET.value, "native:dev"),
            (linter.DockerImageFlagOption.NATIVE_CANDIDATE.value, "native:candidate"),
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
                4. Docker image flag = "native:target"
        When
            - running the linter.
        Then
            - Ensure that the docker images list is empty, and suitable logs (skipping) were written.
        """
        # Mock:
        mocker.patch.object(linter, "get_python_version", return_value=Version("3.8"))
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
        # Crete integration to test on:
        integration_name = "TestIntegration"
        test_integration = pack.create_integration(name=integration_name)
        mocker.patch(
            "demisto_sdk.commands.lint.linter.get_python_version",
            return_value=None,
        )

        # Run lint:
        invalid_docker_image = "demisto/blabla:1.0.0.40800"
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=invalid_docker_image,
            )
            with pytest.raises(ValueError) as e:
                runner._gather_facts(modules={})
                assert "Failed detecting Python version for image" in str(e.value)

    def test_invalid_docker_image_as_docker_image_target(self, mocker, pack):
        """
        This test checks that if an invalid docker image was given as the docker image flag, the linter will try to
        run the unit test on it and will write suitable logs.

        Given
            - An invalid docker image (for example a docker image that doesn't exist in Docker Hub).
        When
            - running the linter with --di native:target --dit invalid_docker_image
        Then
            - Ensure that a suitable log was written.
        """
        mocker.patch(
            "demisto_sdk.commands.lint.linter.get_python_version",
            return_value=None,
        )
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
        from demisto_sdk.commands.common.docker_helper import get_python_version

        get_python_version.cache_clear()

        # Run lint:
        invalid_docker_image = "demisto/blabla:1.0.0.40800"
        with ChangeCWD(pack.repo_path):
            runner = initiate_linter(
                pack.repo_path,
                test_integration.path,
                True,
                docker_image_flag=linter.DockerImageFlagOption.NATIVE_TARGET.value,
                docker_image_target=invalid_docker_image,
            )
            with pytest.raises(ValueError) as e:
                runner._gather_facts(modules={})
                assert "Failed detecting Python version for image" in str(e.value)

    @pytest.mark.parametrize(
        argnames="docker_image_flag, exp_versioned_native_image_name",
        argvalues=[
            (linter.DockerImageFlagOption.NATIVE_GA.value, "native:8.2"),
            (linter.DockerImageFlagOption.NATIVE_MAINTENANCE.value, "native:8.1"),
            (linter.DockerImageFlagOption.NATIVE_DEV.value, "native:dev"),
            (linter.DockerImageFlagOption.NATIVE_TARGET.value, "native:dev"),
            (linter.DockerImageFlagOption.ALL_IMAGES.value, "native:dev"),
            (linter.DockerImageFlagOption.NATIVE_CANDIDATE.value, "native:candidate"),
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
                5. Docker image flag = "native:candidate"
        When
            - running the linter.
        Then
            -
                1-3, 5. Ensure that the docker images list is empty, and suitable logs (skipping) were written.
                4. Ensure that the docker image is only the docker image from the integration yml.
        """
        # Mock:
        mocker.patch.object(linter, "get_python_version", return_value=Version("3.8"))
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
            f"The possible options are: 'native:ga', 'native:maintenance', 'native:dev' and 'native:target'. "
            f"For supported native image versions please see: 'Tests/docker_native_image_config.json'"
        )
        assert runner._facts["images"] == []
        assert str(e.value) == expected_err_msg
        assert (
            log.call_args_list[0][0][0]
            == f"Skipping checks on docker for '{docker_image_flag}' - {expected_err_msg}"
        )

    def test_docker_image_flag_version_not_exists_in_native_config_file(
        self, mocker, repo
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
        from demisto_sdk.commands.common.native_image import NativeImageConfig

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

        repo.docker_native_image_config.write_native_image_config(
            native_image_config_mock
        )

        # this needs to be done because the singleton is executed for the entire test class, and because of that
        # we need to mock the get_instance with the updated native_image_config_mock
        native_image_config = NativeImageConfig.from_path(
            repo.docker_native_image_config.path
        )
        mocker.patch.object(
            NativeImageConfig, "get_instance", return_value=native_image_config
        )

        mocker.patch.object(linter, "get_python_version", return_value=Version("3.8"))
        log = mocker.patch.object(logger, "info")

        # Create integration to test on:
        integration_name = "TestIntegration"
        test_integration = repo.create_pack().create_integration(name="TestIntegration")

        # Run lint:
        docker_image_flag = "native:maintenance"
        with ChangeCWD(repo.path):
            runner = initiate_linter(
                repo.path,
                test_integration.path,
                True,
                docker_image_flag=docker_image_flag,
            )
            runner._gather_facts(modules={})

        # Verify docker images:
        assert runner._facts["images"] == []
        assert str_in_call_args_list(
            log.call_args_list,
            f"Skipping checks on docker for '{docker_image_flag}' - The requested native image:"
            f" '{docker_image_flag}' is not supported. For supported native image versions please see:"
            f" 'Tests/docker_native_image_config.json'",
        )
        assert str_in_call_args_list(
            log.call_args_list,
            f"{integration_name} - Facts - No docker images to run on - "
            f"Skipping run lint in host as well.",
        )


class TestTestsCollection:
    def test_tests_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        integration_path: Path = create_integration(
            content_path=demisto_content, no_tests=False
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert runner._facts["test"]

    def test_tests_not_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
        integration_path: Path = create_integration(
            content_path=demisto_content, no_tests=True
        )
        runner = initiate_linter(demisto_content, integration_path, True)
        runner._gather_facts(modules={})
        assert not runner._facts["test"]

    @pytest.mark.parametrize(
        argnames="all_packs, should_skip",
        argvalues=[
            (True, True),
            (False, False),
        ],
    )
    def test_deprecated_integration(
        self,
        mocker,
        demisto_content: Callable,
        create_integration: Callable,
        all_packs: bool,
        should_skip: bool,
    ):
        """
        Given:
        - Case A: run all packs flag and deprecated integration
        - Case B: do not run on all packs and deprecated integration

        When:
        - calling gather facts

        Then:
        - Case A: gather facts should indicate integration is skipped
        - Case B: gather father should indicate integration is not skipped
        """
        mocker.patch.object(linter.Linter, "_update_support_level")
        integration_path: Path = create_integration(
            content_path=demisto_content, is_deprecated=True
        )
        runner = initiate_linter(
            demisto_content, integration_path, True, all_packs=all_packs
        )
        assert should_skip == runner._gather_facts(modules={})

    @pytest.mark.parametrize(
        argnames="all_packs, should_skip",
        argvalues=[
            (True, True),
            (False, False),
        ],
    )
    def test_deprecated_script(
        self,
        mocker,
        demisto_content: Callable,
        script,
        all_packs,
        should_skip,
    ):
        """
        Given:
        - Case A: run all packs flag and deprecated script
        - Case B: do not run on all packs and deprecated script

        When:
        - calling gather facts

        Then:
        - Case A: gather facts should indicate script is skipped
        - Case B: gather father should indicate script is not skipped
        """
        from demisto_sdk.commands.common.git_util import Repo

        script.yml.update({"deprecated": True})
        mocker.patch.object(Repo, "ignored", return_value=[])
        mocker.patch.object(linter.Linter, "_update_support_level")
        runner = initiate_linter(
            demisto_content, script.path, True, all_packs=all_packs
        )

        assert should_skip == runner._gather_facts(modules={})


class TestLintFilesCollection:
    def test_lint_files_exists(
        self, mocker, demisto_content: Callable, create_integration: Callable
    ):
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
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
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )

        mocker.patch.object(linter.Linter, "_update_support_level")
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
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")
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
        mocker.patch(
            "demisto_sdk.commands.lint.linter.docker_login", return_value=False
        )
        mocker.patch.object(linter.Linter, "_update_support_level")

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

    mocker.patch("demisto_sdk.commands.common.git_util.Repo", return_value=GitMock())
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
            docker_engine=False,
            docker_timeout=30,
        )

        assert linter_instance._pack_abs_dir == Path(expected_path)

        # Delete the temporary directory we created
        if Path(path).is_dir():
            shutil.rmtree(Path(path))


@pytest.mark.parametrize(
    argnames="pack_ignore_content, should_disable_network",
    argvalues=[
        (
            "[file:README.md]\nignore=RM106\n\n[known_words]\ntest1\ntest2\n\n[tests_require_network]\ntest",
            False,
        ),
        ("", True),
        ("[file:README.md]\nignore=RM106\n\n[known_words]\ntest1\ntest2\n\n", True),
        ("[tests_require_network]\ntest1\ntest", False),
        ("[tests_require_network]\ntest1\ntest2", True),
    ],
)
def test_should_use_network(
    pack_ignore_content: str, should_disable_network: bool, pack: Pack
):
    """
    This unit-test testing whether an integration/script needs to use docker network in order to run unit-tests.

    Given:
        - Case A: .pack-ignore file which contains ignored validation, ignored known words and
                   an integration id that needs to use network.
        - Case B: empty .pack-ignore
        - Case C: .pack-ignore without section that defines which integrations/scripts need network
        - Case D: .pack-ignore that has section that defines the integration/script needs network without
                   any ignored validation or ignored known words
        - Case E: .pack-ignore that has section that defines the integration/script does not need network

    When:
        - testing whether the integration/script should disable network on docker.

    Then:
        - Case A: network should not be disabled.
        - Case B: network should be disabled
        - Case C: network should be disabled.
        - Case D: network should not be disabled
        - Case E: network should be disabled.
    """
    from demisto_sdk.commands.lint.linter import Linter

    integration = pack.create_integration("test")
    pack.pack_ignore.write_text(pack_ignore_content)

    _linter = Linter(
        pack_dir=Path(integration.path),
        content_repo=Path(pack.repo_path),
        docker_timeout=0,
        docker_engine=False,
    )

    with ChangeCWD(pack.repo_path):
        assert _linter.should_disable_network() == should_disable_network

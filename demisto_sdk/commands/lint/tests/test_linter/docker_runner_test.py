from dataclasses import dataclass

import pytest

from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.common.docker_helper import DockerBase
from demisto_sdk.commands.lint import linter
from demisto_sdk.commands.lint.linter import Linter


@dataclass
class Container:
    _wait: dict
    _logs: bytes = "".encode("utf-8")

    def start(self):
        return

    def logs(self, **kwargs):
        return self._logs

    def wait(self):
        return self._wait

    def remove(self, **kwargs):
        return


class TestPylint:
    def test_run_pylint_no_errors(self, mocker, linter_obj: Linter):
        # Expected values
        exp_container_exit_code = 0
        exp_container_log = ""
        linter_obj._linter_to_commands()
        # Docker client mocking
        mocker.patch(
            "demisto_sdk.commands.common.docker_helper.DockerBase.create_container"
        )

        linter_obj._docker_client.containers.run("test-image").wait.return_value = {
            "StatusCode": exp_container_exit_code
        }
        linter_obj._docker_client.containers.run(
            "test-image"
        ).logs.return_value = exp_container_log.encode("utf-8")
        act_container_exit_code, act_container_log = linter_obj._docker_run_linter(
            linter="pylint", test_image="test-image", keep_container=False
        )

        assert exp_container_exit_code == act_container_exit_code
        assert exp_container_log == act_container_log

    @pytest.mark.parametrize(
        argnames="exp_container_exit_code, exp_container_log, exp_exit_code, exp_output",
        argvalues=[
            (1, "test", 1, "test"),
            (2, "test", 1, "test"),
            (4, "test", 0, ""),
            (8, "test", 0, ""),
            (16, "test", 0, ""),
            (32, "test", 2, ""),
        ],
    )
    def test_run_pylint_with_errors(
        self,
        mocker,
        linter_obj: Linter,
        exp_container_exit_code: int,
        exp_container_log: str,
        exp_exit_code: int,
        exp_output: str,
    ):
        # Docker client mocking
        mocker.patch.object(
            DockerBase,
            "create_container",
            return_value=Container(
                _wait={"StatusCode": exp_container_exit_code},
                _logs=exp_container_log.encode("utf-8"),
            ),
        )
        linter_obj._linter_to_commands()

        act_exit_code, act_output = linter_obj._docker_run_linter(
            linter="pylint", test_image="test-image", keep_container=False
        )

        assert act_exit_code == exp_exit_code
        assert act_output == exp_output


class TestPytest:
    @pytest.mark.parametrize(
        argnames="exp_container_exit_code, exp_exit_code",
        argvalues=[
            (0, 0),
            (1, 1),
            (2, 1),
            (5, 0),
            (137, 1),
            (139, 1),
            (143, 1),
            (126, 1),
        ],
    )
    def test_run_pytest(
        self,
        mocker,
        linter_obj: Linter,
        exp_container_exit_code: int,
        exp_exit_code: int,
    ):
        exp_test_json = (
            mocker.MagicMock() if exp_container_exit_code in [0, 1, 2, 5] else {}
        )

        # Docker client mocking
        mocker.patch.object(
            DockerBase,
            "create_container",
            return_value=Container(_wait={"StatusCode": exp_container_exit_code}),
        )

        # Docker related mocking
        mocker.patch.object(linter, "json")
        linter.json.loads.return_value = exp_test_json
        mocker.patch.object(linter, "get_file_from_container")

        (
            act_container_exit_code,
            act_output,
            act_test_json,
        ) = linter_obj._docker_run_pytest(
            test_image="test-image", keep_container=False, test_xml="", no_coverage=True
        )

        assert exp_exit_code == act_container_exit_code
        assert exp_test_json == act_test_json


class TestRunLintInContainer:
    """Pylint/Pytest"""

    @pytest.mark.parametrize(
        argnames="no_test, no_pylint, no_pwsh_analyze, no_pwsh_test, no_flake8, no_vulture, pack_type",
        argvalues=[
            (True, True, True, True, True, False, TYPE_PYTHON),
            (True, True, True, True, False, True, TYPE_PYTHON),
            (True, True, True, False, True, True, TYPE_PWSH),
            (True, True, False, True, True, True, TYPE_PWSH),
            (True, False, True, True, True, True, TYPE_PYTHON),
            (False, True, True, True, True, True, TYPE_PYTHON),
        ],
    )
    def test_run_one_lint_check_success(
        self,
        mocker,
        linter_obj,
        lint_files,
        no_test: bool,
        no_pylint: bool,
        no_pwsh_analyze: bool,
        no_pwsh_test: bool,
        no_flake8: bool,
        no_vulture: bool,
        pack_type: str,
    ):
        mocker.patch.dict(
            linter_obj._facts,
            {
                "images": [["image", "3.7"]],
                "test": True,
                "version_two": False,
                "lint_files": lint_files,
                "additional_requirements": [],
            },
        )
        mocker.patch.dict(
            linter_obj._pkg_lint_status,
            {
                "pack_type": pack_type,
            },
        )
        mocker.patch.object(linter_obj, "_docker_image_create")
        linter_obj._docker_image_create.return_value = ("test-image", "")
        mocker.patch.object(linter_obj, "_docker_run_pytest")
        linter_obj._docker_run_pytest.return_value = (0b0, "", {})
        mocker.patch.object(linter_obj, "_docker_run_linter")
        linter_obj._docker_run_linter.return_value = (0b0, "")
        mocker.patch.object(linter_obj, "_docker_run_pwsh_analyze")
        linter_obj._docker_run_pwsh_analyze.return_value = (0b0, {})
        mocker.patch.object(linter_obj, "_docker_run_pwsh_test")
        linter_obj._docker_run_pwsh_test.return_value = (0b0, "")
        linter_obj._run_lint_on_docker_image(
            no_pylint=no_pylint,
            no_test=no_test,
            no_pwsh_analyze=no_pwsh_analyze,
            no_pwsh_test=no_pwsh_test,
            no_flake8=no_flake8,
            no_vulture=no_vulture,
            test_xml="",
            keep_container=False,
            no_coverage=True,
            should_disable_network=True,
        )
        assert linter_obj._pkg_lint_status.get("exit_code") == 0b0
        if not no_test and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_pytest.assert_called_once()
        elif (
            not no_pylint or not no_flake8 or not no_vulture
        ) and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_linter.assert_called_once()
        elif not no_pwsh_analyze and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_analyze.assert_called_once()
        elif not no_pwsh_test and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_test.assert_called_once()

    @pytest.mark.parametrize(
        argnames="image_name, expected_container_name",
        argvalues=[
            # Full image path.
            (
                "docker-io.art.code.pan.run/devtestdemisto/py3-native:8.2.0.123-abcd12345",
                "some_pack-pylint-py3-native_8.2.0.123-abcd12345",
            ),
            # Name and tag only.
            (
                "py3-native:8.2.0.123-abcd12345",
                "some_pack-pylint-py3-native_8.2.0.123-abcd12345",
            ),
            # Starts with invalid character.
            (
                "_py3-native:8.2.0.123-abcd12345",
                "some_pack-pylint-py3-native_8.2.0.123-abcd12345",
            ),
            # Name only.
            ("py3-native-no-tag", "some_pack-pylint-py3-native-no-tag"),
            # Name and tag using an invalid char.
            ("py3-native@some-tag", "some_pack-pylint-py3-native_some-tag"),
        ],
    )
    def test_container_names(
        self, linter_obj: Linter, image_name: str, expected_container_name: str
    ):
        """
        Given: A docker image name
        When: Running lint using docker
        Then: Ensure the container name is valid and as expected.
        """
        linter_obj._linter_to_commands()
        linter_obj._pack_name = "some_pack"

        container_name = linter_obj.get_container_name(
            run_type="pylint", image_name=image_name
        )

        assert container_name == expected_container_name

    @pytest.mark.parametrize(
        argnames="lint_check, lint_check_kwargs",
        argvalues=[
            ("_docker_run_linter", {"linter": "pylint", "keep_container": False}),
            (
                "_docker_run_pytest",
                {"test_xml": "", "keep_container": False, "no_coverage": True},
            ),
            ("_docker_run_pwsh_analyze", {"keep_container": False}),
            ("_docker_run_pwsh_test", {"keep_container": False}),
        ],
    )
    def test_container_names_are_unique_per_tag(
        self,
        mocker,
        lint_files,
        linter_obj: Linter,
        lint_check: str,
        lint_check_kwargs: dict,
    ):
        """
        Given:
            - A native docker image and a native dev docker image to lint with.
            - A lint sub-routine function
        When: Running lint sub-routine using docker on a specific pack.
        Then: Ensure the container names are different.
        """
        exp_container_log = "test"
        # Docker client mocking
        create_container_mock = mocker.patch.object(
            DockerBase,
            "create_container",
            return_value=Container(
                _wait={"StatusCode": 1},
                _logs=exp_container_log.encode("utf-8"),
            ),
        )
        mocker.patch.object(linter, "get_file_from_container")
        mocker.patch.object(linter, "json")

        linter_obj._linter_to_commands()
        linter_obj._pack_name = "some_pack"
        linter_obj._facts["lint_files"] = lint_files

        native_image_example = (
            "docker-io.art.code.pan.run/devtestdemisto/py3-native:8.2.0.123-abcd12345"
        )
        native_dev_image_example = (
            "docker-io.art.code.pan.run/devtestdemisto/py3-native:8.2.0.1234-efgh6789"
        )
        lint_check_func = getattr(linter_obj, lint_check)

        lint_check_kwargs["test_image"] = native_image_example

        lint_check_func(**lint_check_kwargs)

        lint_check_kwargs["test_image"] = native_dev_image_example

        lint_check_func(**lint_check_kwargs)

        container_name_native_image = create_container_mock.call_args_list[
            0
        ].kwargs.get("name")
        container_name_native_dev_image = create_container_mock.call_args_list[
            1
        ].kwargs.get("name")

        assert container_name_native_image != container_name_native_dev_image

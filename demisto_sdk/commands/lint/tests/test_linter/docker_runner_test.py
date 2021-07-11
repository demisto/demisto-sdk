from unittest.mock import DEFAULT

import pytest
from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.lint import linter
from demisto_sdk.commands.lint.linter import Linter


class TestCreateImage:
    def test_build_image_no_errors(self, linter_obj: Linter, demisto_content, create_integration, mocker):
        content_path = demisto_content
        create_integration(content_path=content_path)
        # Expected returns
        exp_test_image_id = 'test-image'
        exp_errors = ""
        # Jinja2 mocking
        mocker.patch.multiple(linter, Environment=DEFAULT, FileSystemLoader=DEFAULT, exceptions=DEFAULT, hashlib=DEFAULT)
        # Facts mocking
        mocker.patch.dict(linter_obj._facts, {
            "images": [],
            "python_version": 0,
            "test": False,
            "lint_files": [],
            "additional_requirements": [],
            "docker_engine": True,
            "env_vars": {
                "CI": True,
                "DEMISTO_LINT_UPDATE_CERTS": "yes"
            }
        })
        mocker.patch.object(linter, 'io')
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        docker_build_response = mocker.MagicMock()
        docker_build_response.short_id = exp_test_image_id

        linter_obj._docker_client.images.build().__getitem__().short_id = exp_test_image_id

        act_test_image_id, act_errors = linter_obj._docker_image_create(docker_base_image=[exp_test_image_id, 3.7])

        assert act_test_image_id == exp_test_image_id
        assert act_errors == exp_errors


class BaseLintTest:
    def get_lint_name(self):
        ...

    def test_run_lint_no_errors(self, mocker, linter_obj: Linter):
        # Expected values
        exp_container_exit_code = 0
        exp_container_log = ""

        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run().wait.return_value = {"StatusCode": exp_container_exit_code}
        linter_obj._docker_client.containers.run().logs.return_value = exp_container_log.encode('utf-8')
        act_container_exit_code, act_container_log = linter_obj._run_linters_in_docker(test_name=self.get_lint_name(),
                                                                                       test_image='test-image',
                                                                                       test_command='test-command',
                                                                                       keep_container=False)

        assert exp_container_exit_code == act_container_exit_code
        assert exp_container_log == act_container_log

    @pytest.mark.parametrize(argnames="exp_container_exit_code, exp_container_log, exp_exit_code, exp_output",
                             argvalues=[(1, "test", 1, "test"),
                                        (2, "test", 1, "test"),
                                        (4, "test", 0, ""),
                                        (8, "test", 0, ""),
                                        (16, "test", 0, ""),
                                        (32, "test", 2, "")])
    def test_run_lint_with_errors(self, mocker, linter_obj: Linter, exp_container_exit_code: int, exp_container_log: str,
                                  exp_exit_code: int, exp_output: str):
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run().wait.return_value = {"StatusCode": exp_container_exit_code}
        linter_obj._docker_client.containers.run().logs.return_value = exp_container_log.encode('utf-8')
        act_exit_code, act_output = linter_obj._run_linters_in_docker(test_name=self.get_lint_name(),
                                                                      test_image='test-image',
                                                                      test_command='test-command',
                                                                      keep_container=False)

        assert act_exit_code == exp_exit_code
        assert act_output == exp_output


class TestPylint(BaseLintTest):
    def get_lint_name(self):
        return 'Pylint'


class TestMypy(BaseLintTest):
    """
        Run mypy in python 3 files in docker container
            - Ensure mypy run in docker container
            - Ensure the PIP_QUIET exist as env variable in the docker container
            - Ensure the right command was prepared (the output redirected to /dev/null)
    """

    def get_lint_name(self):
        return 'Mypy'

    def test_command_passed_to_docker(self, mocker, linter_obj, lint_files):
        """
        Given: - Python file version >= 3

        When: - Run Mypy in docker container

        Then: - Validate the environment passed to the run method of the docker container

        """
        from demisto_sdk.commands.lint.commands_builder import build_mypy_command

        # prepare
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": True,
            "version_two": False,
            "lint_files": lint_files,
            "python_version": 3.7,
            "additional_requirements": []
        })
        mocker.patch.dict(linter_obj._pkg_lint_status, {
            "pack_type": TYPE_PYTHON,
        })
        mocker.patch.object(linter_obj, '_docker_client')
        mocker.patch.object(linter_obj, '_docker_image_create', return_value=("test-image", ""))

        # run
        linter_obj._run_lint_on_docker_image(no_mypy=False, no_pylint=True, no_test=True,
                                             no_pwsh_analyze=True, no_pwsh_test=True, test_xml="",
                                             keep_container=False, no_coverage=True)

        expected_command = build_mypy_command(lint_files, 3.7)
        expected_command == linter_obj._docker_client.containers.run.call_args[1]['command'][0]

    def test_python2_files_not_run_in_docker(self, mocker, linter_obj, lint_files):
        """
        Given: - Python file version < 3

        When: - Call to _run_lint_on_docker_image to run linters in docker image

        Then: - Validate mypy not run in docker as it should run in local os

        """

        # prepare
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "2.7"]],
            "test": True,
            "version_two": False,
            "lint_files": lint_files,
            "python_version": 2.7,
            "additional_requirements": []
        })
        mocker.patch.dict(linter_obj._pkg_lint_status, {
            "pack_type": TYPE_PYTHON,
        })
        mocker.patch.object(linter_obj, '_docker_client')
        mocker.patch.object(linter_obj, '_run_linters_in_docker')
        mocker.patch.object(linter_obj, '_docker_image_create', return_value=("test-image", ""))

        # run
        linter_obj._run_lint_on_docker_image(no_mypy=False, no_pylint=True, no_test=True,
                                             no_pwsh_analyze=True, no_pwsh_test=True, test_xml="",
                                             keep_container=False, no_coverage=True)

        linter_obj._run_linters_in_docker.assert_not_called()

    def test_python3_files_not_run_in_local_os(self, mocker, linter_obj, lint_files):
        """
        Given: - Python file version >= 3

        When: - Run _run_lint_in_host in linter

        Then: - Validate _rin_mypy which is the method for run mypy locally - not run
        """

        # prepare
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": True,
            "version_two": False,
            "lint_files": lint_files,
            "python_version": 3.7,
            "additional_requirements": []
        })
        mocker.patch.dict(linter_obj._pkg_lint_status, {
            "pack_type": TYPE_PYTHON,
        })
        mocker.patch.object(linter_obj, '_run_mypy')

        # run
        linter_obj._run_lint_in_host(no_flake8=True, no_bandit=True,
                                     no_mypy=False, no_vulture=True,
                                     no_xsoar_linter=True)

        # validate
        linter_obj._run_mypy.assert_not_called()


class TestPytest:
    @pytest.mark.parametrize(argnames="exp_container_exit_code, exp_exit_code",
                             argvalues=[(0, 0),
                                        (1, 1),
                                        (2, 1),
                                        (5, 0)])
    def test_run_pytest(self, mocker, linter_obj: Linter, exp_container_exit_code: int, exp_exit_code: int):
        exp_test_json = mocker.MagicMock()

        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run().wait.return_value = {"StatusCode": exp_container_exit_code}

        # Docker related mocking
        mocker.patch.object(linter, 'json')
        linter.json.loads.return_value = exp_test_json
        mocker.patch.object(linter, 'get_file_from_container')

        act_container_exit_code, act_output, act_test_json = linter_obj._docker_run_pytest(test_image='test-image',
                                                                                           keep_container=False,
                                                                                           test_xml="",
                                                                                           no_coverage=True)

        assert exp_exit_code == act_container_exit_code
        assert exp_test_json == act_test_json


class TestRunLintInContainer:
    """Mypy/Pylint/Pytest"""

    @pytest.mark.parametrize(argnames="no_test, no_mypy, no_pylint, no_pwsh_analyze, no_pwsh_test, pack_type",
                             argvalues=[(False, True, True, True, True, TYPE_PYTHON),
                                        (True, False, True, True, True, TYPE_PYTHON),
                                        (True, True, False, True, True, TYPE_PYTHON),
                                        (True, True, True, False, True, TYPE_PYTHON),
                                        (True, True, True, True, False, TYPE_PYTHON)])
    def test_run_one_lint_check_success(self, mocker, linter_obj, lint_files, no_test: bool, no_mypy: bool,
                                        no_pylint: bool, no_pwsh_analyze: bool,
                                        no_pwsh_test: bool, pack_type: str):
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": True,
            "version_two": False,
            "lint_files": lint_files,
            "python_version": 3.7,
            "additional_requirements": []
        })
        mocker.patch.dict(linter_obj._pkg_lint_status, {
            "pack_type": pack_type,
        })
        mocker.patch.object(linter_obj, '_docker_image_create', return_value=("test-image", ""))
        mocker.patch.object(linter_obj, '_docker_run_pytest', return_value=(0b0, '', {}))
        mocker.patch.object(linter_obj, '_run_linters_in_docker', return_value=(0b0, ''))
        mocker.patch.object(linter_obj, '_docker_run_pwsh_analyze', return_value=(0b0, {}))
        mocker.patch.object(linter_obj, '_docker_run_pwsh_test', return_value=(0b0, ''))

        linter_obj._run_lint_on_docker_image(no_mypy=no_mypy,
                                             no_pylint=no_pylint,
                                             no_test=no_test,
                                             no_pwsh_analyze=no_pwsh_analyze,
                                             no_pwsh_test=no_pwsh_test,
                                             test_xml="",
                                             keep_container=False,
                                             no_coverage=True)
        assert linter_obj._pkg_lint_status.get("exit_code") == 0b0
        if not no_test and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_pytest.assert_called_once()
        elif (not no_pylint or not no_mypy) and pack_type == TYPE_PYTHON:
            linter_obj._run_linters_in_docker.assert_called_once()
        elif not no_pwsh_analyze and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_analyze.assert_called_once()
        elif not no_pwsh_test and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_test.assert_called_once()

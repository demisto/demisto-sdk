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


class TestPylint:
    def test_run_pylint_no_errors(self, mocker, linter_obj: Linter):
        # Expected values
        exp_container_exit_code = 0
        exp_container_log = ""

        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run().wait.return_value = {"StatusCode": exp_container_exit_code}
        linter_obj._docker_client.containers.run().logs.return_value = exp_container_log.encode('utf-8')
        act_container_exit_code, act_container_log = linter_obj._docker_run_pylint(test_image='test-image',
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
    def test_run_pylint_with_errors(self, mocker, linter_obj: Linter, exp_container_exit_code: int, exp_container_log: str,
                                    exp_exit_code: int, exp_output: str):
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run().wait.return_value = {"StatusCode": exp_container_exit_code}
        linter_obj._docker_client.containers.run().logs.return_value = exp_container_log.encode('utf-8')
        act_exit_code, act_output = linter_obj._docker_run_pylint(test_image='test-image',
                                                                  keep_container=False)

        assert act_exit_code == exp_exit_code
        assert act_output == exp_output


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
                                                                                           test_xml="")

        assert exp_exit_code == act_container_exit_code
        assert exp_test_json == act_test_json


class TestRunLintInContainer:
    """Pylint/Pytest"""

    @pytest.mark.parametrize(argnames="no_test, no_pylint, no_pwsh_analyze, no_pwsh_test, pack_type",
                             argvalues=[(True, True, False, False, TYPE_PYTHON),
                                        (False, True, True, True, TYPE_PYTHON),
                                        (True, False, True, False, TYPE_PYTHON),
                                        (False, False, False, False, TYPE_PYTHON)])
    def test_run_one_lint_check_success(self, mocker, linter_obj, lint_files, no_test: bool, no_pylint: bool,
                                        no_pwsh_analyze: bool, no_pwsh_test: bool, pack_type: str):
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": True,
            "version_two": False,
            "lint_files": lint_files,
            "additional_requirements": []
        })
        mocker.patch.dict(linter_obj._pkg_lint_status, {
            "pack_type": pack_type,
        })
        mocker.patch.object(linter_obj, '_docker_image_create')
        linter_obj._docker_image_create.return_value = ("test-image", "")
        mocker.patch.object(linter_obj, '_docker_run_pytest')
        linter_obj._docker_run_pytest.return_value = (0b0, '', {})
        mocker.patch.object(linter_obj, '_docker_run_pylint')
        linter_obj._docker_run_pylint.return_value = (0b0, '')
        mocker.patch.object(linter_obj, '_docker_run_pwsh_analyze')
        linter_obj._docker_run_pwsh_analyze.return_value = (0b0, {})
        mocker.patch.object(linter_obj, '_docker_run_pwsh_test')
        linter_obj._docker_run_pwsh_test.return_value = (0b0, '')
        linter_obj._run_lint_on_docker_image(no_pylint=no_pylint,
                                             no_test=no_test,
                                             no_pwsh_analyze=no_pwsh_analyze,
                                             no_pwsh_test=no_pwsh_test,
                                             test_xml="",
                                             keep_container=False,
                                             run_coverage=False)
        assert linter_obj._pkg_lint_status.get("exit_code") == 0b0
        if not no_test and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_pytest.assert_called_once()
        elif not no_pylint and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_pylint.assert_called_once()
        elif not no_pwsh_analyze and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_analyze.assert_called_once()
        elif not no_pwsh_test and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_test.assert_called_once()

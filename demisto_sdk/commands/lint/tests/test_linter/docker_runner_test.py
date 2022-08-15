import pytest

from demisto_sdk.commands.common.constants import TYPE_PWSH, TYPE_PYTHON
from demisto_sdk.commands.lint import linter
from demisto_sdk.commands.lint.linter import Linter


class TestPylint:
    def test_run_pylint_no_errors(self, mocker, linter_obj: Linter):
        # Expected values
        exp_container_exit_code = 0
        exp_container_log = ""
        linter_obj._linter_to_commands()
        # Docker client mocking
        mocker.patch('demisto_sdk.commands.lint.docker_helper.Docker.create_container')

        linter_obj._docker_client.containers.run('test-image').wait.return_value = {"StatusCode": exp_container_exit_code}
        linter_obj._docker_client.containers.run('test-image').logs.return_value = exp_container_log.encode('utf-8')
        act_container_exit_code, act_container_log = linter_obj._docker_run_linter(linter='pylint',
                                                                                   test_image='test-image',
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
        mocker.patch('demisto_sdk.commands.lint.docker_helper.Docker.create_container')
        linter_obj._linter_to_commands()
        linter.Docker.create_container().wait.return_value = {"StatusCode": exp_container_exit_code}
        linter.Docker.create_container().logs.return_value = exp_container_log.encode('utf-8')
        act_exit_code, act_output = linter_obj._docker_run_linter(linter='pylint',
                                                                  test_image='test-image',
                                                                  keep_container=False)

        assert act_exit_code == exp_exit_code
        assert act_output == exp_output


class TestPytest:
    @pytest.mark.parametrize(argnames="exp_container_exit_code, exp_exit_code",
                             argvalues=[(0, 0),
                                        (1, 1),
                                        (2, 1),
                                        (5, 0),
                                        (137, 1),
                                        (139, 1),
                                        (143, 1),
                                        (126, 1)])
    def test_run_pytest(self, mocker, linter_obj: Linter, exp_container_exit_code: int, exp_exit_code: int):
        exp_test_json = mocker.MagicMock() if exp_container_exit_code in [0, 1, 2, 5] else {}

        # Docker client mocking
        mocker.patch('demisto_sdk.commands.lint.docker_helper.Docker.create_container')
        linter.Docker.create_container().wait.return_value = {"StatusCode": exp_container_exit_code}

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
    """Pylint/Pytest"""

    @pytest.mark.parametrize(argnames="no_test, no_pylint, no_pwsh_analyze, no_pwsh_test, no_flake8, no_vulture, pack_type",
                             argvalues=[(True, True, True, True, True, False, TYPE_PYTHON),
                                        (True, True, True, True, False, True, TYPE_PYTHON),
                                        (True, True, True, False, True, True, TYPE_PWSH),
                                        (True, True, False, True, True, True, TYPE_PWSH),
                                        (True, False, True, True, True, True, TYPE_PYTHON),
                                        (False, True, True, True, True, True, TYPE_PYTHON)])
    def test_run_one_lint_check_success(self, mocker, linter_obj, lint_files, no_test: bool, no_pylint: bool,
                                        no_pwsh_analyze: bool, no_pwsh_test: bool, no_flake8: bool, no_vulture: bool, pack_type: str):
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
        mocker.patch.object(linter_obj, '_docker_run_linter')
        linter_obj._docker_run_linter.return_value = (0b0, '')
        mocker.patch.object(linter_obj, '_docker_run_pwsh_analyze')
        linter_obj._docker_run_pwsh_analyze.return_value = (0b0, {})
        mocker.patch.object(linter_obj, '_docker_run_pwsh_test')
        linter_obj._docker_run_pwsh_test.return_value = (0b0, '')
        linter_obj._run_lint_on_docker_image(no_pylint=no_pylint,
                                             no_test=no_test,
                                             no_pwsh_analyze=no_pwsh_analyze,
                                             no_pwsh_test=no_pwsh_test,
                                             no_flake8=no_flake8,
                                             no_vulture=no_vulture,
                                             test_xml="",
                                             keep_container=False,
                                             no_coverage=True)
        assert linter_obj._pkg_lint_status.get("exit_code") == 0b0
        if not no_test and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_pytest.assert_called_once()
        elif (not no_pylint or not no_flake8 or not no_vulture) and pack_type == TYPE_PYTHON:
            linter_obj._docker_run_linter.assert_called_once()
        elif not no_pwsh_analyze and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_analyze.assert_called_once()
        elif not no_pwsh_test and pack_type == TYPE_PWSH:
            linter_obj._docker_run_pwsh_test.assert_called_once()

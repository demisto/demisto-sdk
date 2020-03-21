from demisto_sdk.commands.lint.linter import Linter
from demisto_sdk.commands.lint import linter
from unittest.mock import DEFAULT
import pytest
import docker.errors
from unittest.mock import MagicMock


class TestCreateImage:
    def test_build_image_no_errors(self, linter_obj: Linter, mocker):
        # Expected returns
        exp_test_image_id = 'test-image'
        exp_errors = ""
        # Jinja2 mocking
        mocker.patch.multiple(linter, Environment=DEFAULT, FileSystemLoader=DEFAULT, exceptions=DEFAULT)
        # Tempfile pack mocking
        mocker.patch.object(linter, 'tempfile')
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        docker_build_response = mocker.MagicMock()
        docker_build_response.short_id = exp_test_image_id
        linter_obj._docker_client.images.build.return_value = [docker_build_response]

        act_test_image_id, act_errors = linter_obj._docker_image_create(docker_base_image=[exp_test_image_id, 3.7],
                                                                        no_test=False)

        assert act_test_image_id == exp_test_image_id
        assert act_errors == exp_errors
        assert linter_obj._docker_client.images.build.call_count == 1

    def test_build_docker_build_exception(self, mocker, linter_obj: Linter):
        import docker.errors
        # Expected returns
        exp_test_image_id = ''
        exp_errors = "my_error"
        # Jinja2 mocking
        mocker.patch.multiple(linter, Environment=DEFAULT, FileSystemLoader=DEFAULT, exceptions=DEFAULT)
        # Tempfile pack mocking
        mocker.patch.object(linter, 'tempfile')
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')

        linter_obj._docker_client.images.build.side_effect = docker.errors.BuildError(reason=exp_errors,
                                                                                      build_log=mocker.Mock())

        act_test_image_id, act_errors = linter_obj._docker_image_create(docker_base_image=[exp_test_image_id, 3.7],
                                                                        no_test=False)

    def test_build_with_docker_api_exception(self, mocker, linter_obj: Linter):
        # Expected returns
        exp_test_image_id = ''
        exp_errors = "my_error"
        # Jinja2 mocking
        mocker.patch.multiple(linter, Environment=DEFAULT, FileSystemLoader=DEFAULT, exceptions=DEFAULT)
        # Tempfile pack mocking
        mocker.patch.object(linter, 'tempfile')
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')

        linter_obj._docker_client.images.build.side_effect = docker.errors.APIError(message=exp_errors)

        act_test_image_id, act_errors = linter_obj._docker_image_create(docker_base_image=[exp_test_image_id, 3.7],
                                                                        no_test=False)

        assert act_test_image_id == exp_test_image_id
        assert act_errors == exp_errors
        assert linter_obj._docker_client.images.build.call_count == 2


class TestPylint:
    def test_run_pylint_no_errors(self, mocker, linter_obj: Linter):
        # Expected values
        exp_container_exit_code = 0
        exp_container_log = ""

        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run.return_value = exp_container_log

        act_container_exit_code, act_container_log = linter_obj._docker_run_pylint(test_image='test-image',
                                                                                   keep_container=False)

        assert exp_container_exit_code == act_container_exit_code
        assert exp_container_log == act_container_log

    @pytest.mark.parametrize(argnames="exp_container_exit_code, exp_container_log, exp_exit_code, exp_log",
                             argvalues=[(1, "test", 1, "test"),
                                        (2, "test", 1, "test"),
                                        (4, "test", 0, ""),
                                        (8, "test", 0, ""),
                                        (16, "test", 0, ""),
                                        (32, "test", 2, "")])
    def test_run_pylint_with_errors(self, mocker, linter_obj: Linter, exp_container_exit_code: int, exp_container_log: str,
                                    exp_exit_code: int, exp_log: str):
        # Docker client mocking
        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run.return_value = exp_container_log
        linter_obj._docker_client.containers.run.side_effect = docker.errors.ContainerError(container=MagicMock(),
                                                                                            exit_status=exp_container_exit_code,
                                                                                            command=MagicMock(),
                                                                                            image=MagicMock(),
                                                                                            stderr=MagicMock())
        linter_obj._docker_client.containers.run.side_effect.container.logs.return_value = exp_container_log.encode('utf-8')

        act_container_exit_code, act_container_log = linter_obj._docker_run_pylint(test_image='test-image',
                                                                                   keep_container=False)

        assert exp_exit_code == act_container_exit_code
        assert exp_log == act_container_log

    @pytest.mark.parametrize(argnames="exception",
                             argvalues=[docker.errors.APIError, docker.errors.ImageNotFound])
    def test_run_pylint_with_docker_exception(self, mocker, linter_obj: Linter, exception):
        # Expected values
        exp_container_exit_code = 2
        exp_container_log = "my-error"

        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run.side_effect = exception(message=exp_container_log)

        act_container_exit_code, act_container_log = linter_obj._docker_run_pylint(test_image='test-image',
                                                                                   keep_container=False)

        assert exp_container_exit_code == act_container_exit_code
        assert exp_container_log == act_container_log


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
        if exp_container_exit_code:
            linter_obj._docker_client.containers.run.side_effect = docker.errors.ContainerError(container=MagicMock(),
                                                                                                exit_status=exp_container_exit_code,
                                                                                                command=MagicMock(),
                                                                                                image=MagicMock(),
                                                                                                stderr=MagicMock())

        # Docker related mocking
        mocker.patch.object(linter, 'json')
        linter.json.loads.return_value = exp_test_json
        mocker.patch.object(linter, 'get_file_from_container')

        act_container_exit_code, act_test_json = linter_obj._docker_run_pytest(test_image='test-image',
                                                                               keep_container=False,
                                                                               test_xml="")

        assert exp_exit_code == act_container_exit_code
        assert exp_test_json == act_test_json

    @pytest.mark.parametrize(argnames="exception",
                             argvalues=[docker.errors.APIError, docker.errors.ImageNotFound])
    def test_run_pytes_with_docker_exception(self, mocker, linter_obj: Linter, exception):
        # Expected values
        exp_container_exit_code = 2
        exp_container_log = "my-error"

        mocker.patch.object(linter_obj, '_docker_client')
        linter_obj._docker_client.containers.run.side_effect = exception(message=exp_container_log)

        act_container_exit_code, act_test_json = linter_obj._docker_run_pytest(test_image='test-image',
                                                                               keep_container=False,
                                                                               test_xml="")

        assert exp_container_exit_code == act_container_exit_code
        assert act_test_json == {}


class TestRunLintInContainer:
    """Pylint/Pytest"""
    @pytest.mark.parametrize(argnames="no_test, no_pylint",
                             argvalues=[(True, True),
                                        (False, True),
                                        (True, False),
                                        (False, False)])
    def test_run_one_lint_check_success(self, mocker, linter_obj, lint_files, no_test: bool, no_pylint: bool):
        mocker.patch.dict(linter_obj._facts, {
            "images": [["image", "3.7"]],
            "test": True,
            "version_two": False,
            "lint_files": lint_files,
            "additional_requirements": []
        })
        mocker.patch.object(linter_obj, '_docker_image_create')
        linter_obj._docker_image_create.return_value = ("test-image", "")
        mocker.patch.object(linter_obj, '_docker_run_pytest')
        linter_obj._docker_run_pytest.return_value = (0b0, {})
        mocker.patch.object(linter_obj, '_docker_run_pylint')
        linter_obj._docker_run_pylint.return_value = (0b0, '')
        linter_obj._run_lint_on_docker_image(no_pylint=no_pylint,
                                             no_test=no_test,
                                             test_xml="",
                                             keep_container=False)
        assert linter_obj._pkg_lint_status.get("exit_code") == 0b0
        if not no_test:
            linter_obj._docker_run_pytest.assert_called_once()
        elif not no_pylint:
            linter_obj._docker_run_pylint.assert_called_once()

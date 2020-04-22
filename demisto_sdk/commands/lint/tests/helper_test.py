import pytest


def test_validate_env(mocker) -> None:
    from demisto_sdk.commands.lint import helpers
    mocker.patch.object(helpers, 'run_command_os')
    helpers.run_command_os.side_effect = [('python2', '', ''), ('flake8, mypy, vultue', '', '')]
    helpers.validate_env()

    assert helpers.run_command_os.call_count == 2


EXIT_CODES = {
    "flake8": 0b1,
    "bandit": 0b10,
    "mypy": 0b100,
    "vulture": 0b1000,
    "pytest": 0b10000,
    "pylint": 0b100000,
    "image": 0b1000000,
    "pwsh_analyze": 0b10000000,
    "pwsh_test": 0b100000000
}


@pytest.mark.parametrize(argnames="no_flake8, no_bandit, no_mypy, no_pylint, no_vulture, no_test, no_pwsh_analyze, "
                                  "no_pwsh_test, docker_engine, expected_value",
                         argvalues=[(True, True, True, True, True, True, True, True, True, 0b11111111),
                                    (True, False, True, True, True, True, True, True, True, 0b11111101),
                                    (True, False, True, True, True, True, False, True, True, 0b10111101)])
def test_build_skipped_exit_code(no_flake8: bool, no_bandit: bool, no_mypy: bool, no_pylint: bool, no_vulture: bool,
                                 no_test: bool, no_pwsh_analyze: bool, no_pwsh_test: bool, docker_engine: bool,
                                 expected_value: int) -> bool:
    from demisto_sdk.commands.lint.helpers import build_skipped_exit_code

    assert expected_value == build_skipped_exit_code(no_flake8, no_bandit, no_mypy, no_pylint, no_vulture, no_test,
                                                     no_pwsh_analyze, no_pwsh_test, docker_engine)


@pytest.mark.parametrize(argnames="image, output, expected", argvalues=[('alpine', b'3.7\n', 3.7),
                                                                        ('alpine-3', b'2.7\n', 2.7)])
def test_get_python_version_from_image(image: str, output: bytes, expected: float, mocker):
    from demisto_sdk.commands.lint import helpers
    mocker.patch.object(helpers, 'docker')
    helpers.docker.from_env().containers.run().logs.return_value = output
    assert expected == helpers.get_python_version_from_image(image)


@pytest.mark.parametrize(argnames="archive_response, expected_count, expected_exception",
                         argvalues=[
                             ([False, True], 2, False),
                             ([True], 1, False),
                             ([False, False], 2, True)
                         ])
def test_copy_dir_to_container(mocker, archive_response: bool, expected_count: int, expected_exception: bool):
    from demisto_sdk.commands.lint import helpers
    mocker.patch.object(helpers, 'docker')
    mocker.patch.object(helpers, 'tarfile')
    mocker.patch.object(helpers, 'os')
    mock_container = mocker.MagicMock()
    mock_container_path = mocker.MagicMock()
    mock_host_path = mocker.MagicMock()
    mock_container.put_archive.side_effect = archive_response
    if expected_exception:
        with pytest.raises(Exception):
            helpers.copy_dir_to_container(mock_container, mock_container_path, mock_host_path)
    else:
        helpers.copy_dir_to_container(mock_container, mock_container_path, mock_host_path)

    assert mock_container.put_archive.call_count == expected_count

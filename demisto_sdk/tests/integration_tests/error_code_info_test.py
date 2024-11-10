import pytest
from typer.testing import CliRunner

from demisto_sdk.__main__ import app


@pytest.mark.parametrize("error_code", ["BC100"])
def test_error_code_info_end_to_end(mocker, error_code):
    """
    Given
     - an error code

    When
     - executing the error-code command via cli

    Then
     - make sure the command does not fail and exits gracefully.
    """

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["error-code", "-i", error_code])

    assert result.exit_code == 0
    assert not result.exception
    assert result.output


def test_error_code_info_sanity(mocker, monkeypatch):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["error-code", "-i", "BA100"])

    assert all(
        [
            current_str in result.output
            for current_str in ["BA100", "should always be -1"]
        ]
    )
    assert result.exit_code == 0


def test_error_code_info_refactored_validate(mocker, monkeypatch):
    from demisto_sdk.commands.validate.validators.DO_validators.DO106_docker_image_is_latest_tag import (
        DockerImageTagIsNotOutdated,
    )

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["error-code", "-i", "DO106"])

    assert all(
        [
            current_str in result.output
            for current_str in [
                f"Error Code\t{DockerImageTagIsNotOutdated.error_code}",
                f"Description\t{DockerImageTagIsNotOutdated.description}",
                f"Rationale\t{DockerImageTagIsNotOutdated.rationale}",
            ]
        ]
    )
    assert result.exit_code == 0


def test_error_code_info_failure(mocker, monkeypatch):
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, ["error-code", "-i", "KELLER"])

    assert "No such error" in result.output
    assert result.exit_code == 1

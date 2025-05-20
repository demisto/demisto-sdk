import pytest
from typer.testing import CliRunner

from demisto_sdk.__main__ import app


@pytest.mark.parametrize(
    "args, expected_stdout",
    [
        (["-j", "123"], "please include a `command` argument."),
        (["-j", "123", "-c", "ttt"], "please include a `prefix` argument."),
        (["-j", "123", "-c", "ttt", "-p", "qwe"], None),
    ],
)
def test_generate_outputs_json_to_outputs_flow(
    mocker, monkeypatch, args, expected_stdout
):
    """
    Given
        - Bad inputs
        - One good input
    When
        - Generate outputs command is run (json_to_outputs flow)

    Then
        - Ensure that the outputs are valid
    """
    import demisto_sdk.commands.generate_outputs.generate_outputs as go

    mocker.patch.object(go, "json_to_outputs", return_value="None")

    runner = CliRunner()
    result = runner.invoke(app, ["generate-outputs", *args], catch_exceptions=False)
    if expected_stdout:
        assert expected_stdout in result.output


@pytest.mark.parametrize(
    "args, expected_stdout, expected_exit_code",
    [
        (["-e"], "requires an argument", 2),
        (["-e", "<example>"], "command please include an `input` argument", 0),
        (["-e", "<example>", "-i", "123"], "Input file 123 was not found", 0),
    ],
)
def test_generate_outputs_generate_integration_context_flow(
    mocker, args, expected_stdout, expected_exit_code
):
    """
    Given
        - Bad inputs
        - One good input
    When
        - Generate outputs command is run (generate_integration_context flow)

    Then
        - Ensure that the outputs are valid
    """

    import demisto_sdk.commands.generate_outputs.generate_outputs as go

    mocker.patch.object(go, "generate_integration_context", return_value="None")

    runner = CliRunner()
    result = runner.invoke(app, ["generate-outputs", *args], catch_exceptions=False)
    assert result.exit_code == expected_exit_code
    if expected_exit_code == 0:
        assert expected_stdout in result.output

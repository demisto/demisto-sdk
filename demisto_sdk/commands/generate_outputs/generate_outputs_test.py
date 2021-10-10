import pytest
from click.testing import CliRunner

import demisto_sdk.__main__ as main


@pytest.mark.parametrize('args, excpected_stdout', [
    (['-j', '123'], 'please include a `command` argument.'),
    (['-j', '123', '-c', 'ttt'], 'please include a `prefix` argument.'),
    (['-j', '123', '-c', 'ttt', '-p', 'qwe'], ''),
])
def test_generate_outputs_json_to_outputs_flow(mocker, args, excpected_stdout):
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
    mocker.patch.object(go, 'json_to_outputs', return_value='None')

    runner = CliRunner()
    result = runner.invoke(main.generate_outputs, args=args,
                           catch_exceptions=False)
    assert excpected_stdout in result.output


@pytest.mark.parametrize('args, excpected_stdout', [
    ('', 'To use the generate_integration_context version'),
    (['-e', '<example>'], 'command please include an `input` argument'),
    (['-e', '<example>', '-i', '123'], 'Input file 123 was not found'),
])
def test_generate_outputs_generate_integration_context_flow(mocker, args,
                                                            excpected_stdout):
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
    mocker.patch.object(go, 'generate_integration_context', return_value='None')

    runner = CliRunner()
    result = runner.invoke(main.generate_outputs, args=args,
                           catch_exceptions=False)
    assert excpected_stdout in result.output

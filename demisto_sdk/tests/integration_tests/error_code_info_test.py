from click.testing import CliRunner

from demisto_sdk.__main__ import main


def test_error_code_info_sanity():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["error-code", "-i", "BA100"])

    assert "Function: wrong_version(expected='-1')" in result.output
    assert (
        "The version for our files should always be -1, please update the file."
        in result.output
    )
    assert result.exit_code == 0


def test_error_code_info_failure():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["error-code", "-i", "KELLER"])

    assert "No such error" in result.output
    assert result.exit_code == 1

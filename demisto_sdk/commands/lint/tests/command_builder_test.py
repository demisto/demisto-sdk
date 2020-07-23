from pathlib import Path
from unittest.mock import MagicMock

import pytest

values = [[Path("file1.py")], [Path("file1.py"), Path("file2.py")]]


@pytest.mark.parametrize(argnames="py_num , expected_exec", argvalues=[(3.7, 'python3'), (2.7, 'python')])
def test_get_python_exec(py_num, expected_exec):
    """Get python exec"""
    from demisto_sdk.commands.lint.commands_builder import get_python_exec
    assert expected_exec == get_python_exec(py_num)


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_flak8_command(files):
    """Build flake8 command"""
    from demisto_sdk.commands.lint.commands_builder import build_flake8_command
    output = build_flake8_command(files, 3.8)
    files = [str(file) for file in files]
    expected = f"python3 -m flake8 {' '.join(files)}"
    assert output == expected


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_bandit_command(files):
    """Build bandit command"""
    from demisto_sdk.commands.lint.commands_builder import build_bandit_command
    output = build_bandit_command(files)
    files = [str(file) for file in files]
    expected = f"python3 -m bandit -lll -iii -a file --exclude=CommonServerPython.py,demistomock.py," \
               f"CommonServerUserPython.py," \
               f"conftest.py,venv -q -r {','.join(files)}"
    assert expected == output


@pytest.mark.parametrize(argnames="files, py_num", argvalues=[(values[0], "2.7"), (values[1], "3.7")])
def test_build_mypy_command(files, py_num):
    """Build Mypy command"""
    from demisto_sdk.commands.lint.commands_builder import build_mypy_command
    output = build_mypy_command(files, py_num)
    files = [str(file) for file in files]
    expected = f"python3 -m mypy --python-version {py_num} --check-untyped-defs --ignore-missing-imports " \
               f"--follow-imports=silent --show-column-numbers --show-error-codes --pretty --allow-redefinition " \
               f"--cache-dir=/dev/null {' '.join(files)}"
    assert expected == output


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_vulture_command(files, mocker):
    """Build bandit command"""
    from demisto_sdk.commands.lint.commands_builder import build_vulture_command
    from demisto_sdk.commands.lint import commands_builder
    mocker.patch.object(commands_builder, 'os')
    commands_builder.os.environ.get.return_value = 20
    output = build_vulture_command(files, Path('~/dev/content/'), 2.7)
    files = [str(item) for item in files]
    expected = f"python -m vulture --min-confidence 20 --exclude=CommonServerPython.py,demistomock.py," \
               f"CommonServerUserPython.py,conftest.py,venv {' '.join(files)}"
    assert expected == output


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_pylint_command(files):
    """Build Pylint command"""
    from demisto_sdk.commands.lint.commands_builder import build_pylint_command
    output = build_pylint_command(files)
    files = [str(file) for file in files]
    expected = "python -m pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py," \
               "conftest.py,venv -E -d duplicate-string-formatting-argument" \
               f" --generated-members=requests.packages.urllib3,requests.codes.ok {' '.join(files)}"
    assert expected == output


def test_build_pytest_command_1():
    """Build Pytest command without json"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command
    command = "python -m pytest --junitxml=/devwork/report_pytest.xml"
    assert command == build_pytest_command(test_xml="test")


def test_build_pytest_command_2():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command
    command = "python -m pytest --junitxml=/devwork/report_pytest.xml --json=/devwork/report_pytest.json"
    assert command == build_pytest_command(test_xml="test",
                                           json=True)


def test_build_pwsh_analyze():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pwsh_analyze_command
    file = MagicMock()
    command = f"pwsh -Command Invoke-ScriptAnalyzer -EnableExit -Path {file.name}"
    assert command == build_pwsh_analyze_command(file)


def test_build_pwsh_test():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pwsh_test_command
    command = 'pwsh -Command Invoke-Pester -Configuration \'@{Run=@{Exit=$true}; Output=@{Verbosity="Detailed"}}\''
    assert command == build_pwsh_test_command()

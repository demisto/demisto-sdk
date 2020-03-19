import pytest
from pathlib import Path

values = [[Path("file1.py")], [Path("file1.py"), Path("file2.py")]]


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_flak8_command(files):
    """Build flake8 command"""
    from demisto_sdk.commands.lint.commands_builder import build_flake8_command
    output = build_flake8_command(files)
    files = [str(file) for file in files]
    expected = f"python3 -m flake8 --max-line-length 130 " \
        f"--ignore=W293,W504,W291,W605,F405,F403,E999,W503,F841,E302,C901," \
        f"F821,E402 --exclude=CommonServerPython.py,demistomock.py,CommonServerUserPython.py,conftest.py,venv " \
        f"{' '.join(files)}"
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
    output = build_vulture_command(files, Path('~/dev/content/'))
    files = [str(item) for item in files]
    expected = f"python3 -m vulture --min-confidence 20 --exclude=CommonServerPython.py,demistomock.py," \
               f"CommonServerUserPython.py,conftest.py,venv {' '.join(files)}"
    assert expected == output


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_pylint_command(files):
    """Build Pylint command"""
    from demisto_sdk.commands.lint.commands_builder import build_pylint_command
    output = build_pylint_command(files)
    files = [str(file) for file in files]
    expected = "python -m pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py," \
               "conftest.py,venv -E -d duplicate-string-formatting-argument --msg-template='{path} ({line}): {msg}'" \
               f" --generated-members=requests.packages.urllib3,requests.codes.ok {' '.join(files)}"
    assert expected == output


def test_build_pytest_command_1():
    """Build Pytest command without json"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command
    command = "pytest -q --junitxml=/devwork/report_pytest.xml"
    assert command == build_pytest_command(test_xml="test")


def test_build_pytest_command_2():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command
    command = "pytest -q --junitxml=/devwork/report_pytest.xml --json=/devwork/report_pytest.json"
    assert command == build_pytest_command(test_xml="test",
                                           json=True)

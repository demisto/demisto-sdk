from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock

import pytest

values = [[Path("file1.py")], [Path("file1.py"), Path("file2.py")]]


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_flak8_command(files):
    """Build flake8 command"""
    from demisto_sdk.commands.lint.commands_builder import build_flake8_command

    output = build_flake8_command(files)
    files = [file.name for file in files]
    expected = (
        f"flake8 --ignore=W605,F403,F405,W503 "
        "--exclude=_script_template_docker.py,./CommonServerPython.py,./demistomock.py "
        "--max-line-length 130 "
        "--per-file-ignores=nudge_external_prs.py:E231,E251,E999 "
        f"{' '.join(files)}"
    )
    assert output == expected


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_xsoar_linter_py3_command(files):
    """Build xsoar linter command"""
    from demisto_sdk.commands.lint.commands_builder import build_xsoar_linter_command

    output = build_xsoar_linter_command(files, "base")
    files = [str(file) for file in files]
    expected = (
        f"pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py,"
        "conftest.py,.venv -E --disable=all --msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'"
        " --enable=E9002,E9003,E9004,E9005,E9006,E9007,E9010,E9011,E9012,W9013, --load-plugins "
        f"base_checker, {' '.join(files)}"
    )
    assert output == expected


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_xsoar_linter_py2_command(files):
    """Build xsoar linter command"""
    from demisto_sdk.commands.lint.commands_builder import build_xsoar_linter_command

    output = build_xsoar_linter_command(files, "base")
    files = [str(file) for file in files]
    expected = (
        f"pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py,"
        "conftest.py,.venv -E --disable=all --msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}' "
        "--enable=E9002,E9003,E9004,E9005,E9006,E9007,E9010,E9011,E9012,W9013, --load-plugins "
        f"base_checker, {' '.join(files)}"
    )
    assert output == expected


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_xsoar_linter_no_base_command(files):
    """Build xsoar linter command"""
    from demisto_sdk.commands.lint.commands_builder import build_xsoar_linter_command

    output = build_xsoar_linter_command(files, "unsupported")
    files = [str(file) for file in files]
    expected = (
        "pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py,"
        "conftest.py,.venv -E --disable=all --msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}' "
        f"--enable= {' '.join(files)}"
    )
    assert output == expected


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_bandit_command(files):
    """Build bandit command"""
    from demisto_sdk.commands.lint.commands_builder import build_bandit_command

    output = build_bandit_command(files)
    files = [str(file) for file in files]
    expected = (
        "bandit -ll -iii -s B301,B303,B310,B314,B318 -a file --exclude=CommonServerPython.py,demistomock.py,"
        "CommonServerUserPython.py,"
        "conftest.py,.venv -q --format custom --msg-template "
        "'{abspath}:{line}: {test_id} [Severity: {severity} Confidence: {confidence}] {msg}' "
        f"-r {','.join(files)}"
    )
    assert expected == output


@pytest.mark.parametrize(
    argnames="files, py_num, content_path",
    argvalues=[(values[0], "2.7", None), (values[1], "3.7", Path("test_path"))],
)
def test_build_mypy_command(files, py_num, content_path):
    """Build Mypy command"""
    from demisto_sdk.commands.lint.commands_builder import build_mypy_command

    expected_cache_dir = "test_path/.mypy_cache" if content_path else "/dev/null"
    output = build_mypy_command(files, py_num, content_path)
    files = [str(file) for file in files]
    expected = (
        f"mypy --python-version {py_num} --check-untyped-defs --ignore-missing-imports "
        f"--follow-imports=silent --show-column-numbers --show-error-codes --pretty --allow-redefinition "
        f"--show-absolute-path --show-traceback --cache-dir={expected_cache_dir} {' '.join(files)}"
    )
    assert expected == output


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_vulture_command(files, mocker):
    """Build bandit command"""
    from demisto_sdk.commands.lint import commands_builder
    from demisto_sdk.commands.lint.commands_builder import build_vulture_command

    mocker.patch.object(commands_builder, "os")
    commands_builder.os.environ.get.return_value = 20
    output = build_vulture_command(files, Path("~/dev/content/"))
    files = [item.name for item in files]
    expected = (
        f"vulture --min-confidence 20 --exclude=CommonServerPython.py,demistomock.py,"
        f"CommonServerUserPython.py,conftest.py,.venv {' '.join(files)}"
    )
    assert expected == output


@pytest.mark.parametrize(argnames="files", argvalues=values)
def test_build_pylint_command(files):
    """Build Pylint command"""
    from demisto_sdk.commands.lint.commands_builder import build_pylint_command

    output = build_pylint_command(files)
    files = [file.name for file in files]
    expected = (
        "pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py,"
        "conftest.py,.venv -E --disable=bad-option-value -d duplicate-string-formatting-argument "
        "--msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'"
        f" --generated-members=requests.packages.urllib3,requests.codes.ok {' '.join(files)}"
    )
    assert expected == output


def test_build_pylint_command_3_9_docker():
    """Build Pylint command"""
    from demisto_sdk.commands.lint.commands_builder import build_pylint_command

    NamedFile = namedtuple("File", "name")
    files = [NamedFile("file1")]
    output = build_pylint_command(files, "3.9")
    assert output.endswith(files[0].name)
    assert "disable=bad-option-value,unsubscriptable-object" in output


def test_build_pylint_command_3_9_1_docker():
    """Build Pylint command"""
    from demisto_sdk.commands.lint.commands_builder import build_pylint_command

    NamedFile = namedtuple("File", "name")
    files = [NamedFile("file1")]
    output = build_pylint_command(files, "3.9.1")
    assert output.endswith(files[0].name)
    assert "disable=bad-option-value,unsubscriptable-object" in output


def test_build_pytest_command_1():
    """Build Pytest command without json"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command

    command = "pytest -ra --override-ini='asyncio_mode=auto' --junitxml=/devwork/report_pytest.xml"
    assert command == build_pytest_command(test_xml="test")


def test_build_pytest_command_2():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command

    command = (
        "pytest -ra --override-ini='asyncio_mode=auto' --junitxml=/devwork/report_pytest.xml "
        "--json=/devwork/report_pytest.json"
    )
    assert command == build_pytest_command(test_xml="test", json=True)


def test_build_pytest_command_3():
    """Build Pytest command with cov"""
    from demisto_sdk.commands.lint.commands_builder import build_pytest_command

    command = "pytest -ra --override-ini='asyncio_mode=auto' --junitxml=/devwork/report_pytest.xml --cov-report= --cov=test"
    assert command == build_pytest_command(test_xml="test", cov="test")


def test_build_pwsh_analyze():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pwsh_analyze_command

    file = MagicMock()
    command = f"pwsh -Command Invoke-ScriptAnalyzer -EnableExit -Severity Error -Path {file.name}"
    assert command == build_pwsh_analyze_command(file)


def test_build_pwsh_test():
    """Build Pytest command with json"""
    from demisto_sdk.commands.lint.commands_builder import build_pwsh_test_command

    command = "pwsh -Command Invoke-Pester -Configuration '@{Run=@{Exit=$true}; Output=@{Verbosity=\"Detailed\"}}'"
    assert command == build_pwsh_test_command()

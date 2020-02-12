# import pytest
#
#
# @pytest.mark.parametrize(argnames="file", argvalues=["file1.py", "file2.py"])
# def test_build_flak8_command(file):
#     """Build flake8 command"""
#     from demisto_sdk.commands.lint.commands_builder import build_flake8_command
#     command = f"python3 -m flake8 --max-line-length 130 " \
#               f"--ignore=W293,W504,W291,W605,F405,F403,E999,W503,F841,E302,C901," \
#               f"F821 --exclude=CommonServerPython.py,demistomock.py,CommonServerUserPython.py,conftest.py,venv {file}"
#     assert command == build_flake8_command(file)
#
#
# @pytest.mark.parametrize(argnames="file", argvalues=["file1.py", "file2.py"])
# def test_build_bandit_command(file):
#     """Build flake8 command"""
#     from demisto_sdk.commands.lint.commands_builder import build_bandit_command
#     command = f"python3 -m bandit -lll -iii -a file --exclude=CommonServerPython.py,demistomock.py," \
#               f"CommonServerUserPython.py," \
#               f"conftest.py,venv -q -r {file}"
#     assert command == build_bandit_command(file)
#
#
# @pytest.mark.parametrize(argnames="file, py_num", argvalues=[("file1.py", "2.7"), ("file2.py", "3.7")])
# def test_build_mypy_command(file, py_num):
#     """Build flake8 command"""
#     from demisto_sdk.commands.lint.commands_builder import build_mypy_command
#     command = f"python3 -m mypy --python-version {py_num} --check-untyped-defs --ignore-missing-imports " \
#               f"--follow-imports=silent --show-column-numbers --show-error-codes --pretty --allow-redefinition " \
#               f"--cache-dir=/dev/null {file}"
#     assert command == build_mypy_command(file, py_num)
#
#
# @pytest.mark.parametrize(argnames="file", argvalues=["file1.py", "file2.py"])
# def test_build_pylint_command(file):
#     """Build flake8 command"""
#     from demisto_sdk.commands.lint.commands_builder import build_pylint_command
#     command = "python -m pylint --ignore=CommonServerPython.py,demistomock.py,CommonServerUserPython.py," \
#               "conftest.py,venv -E -d duplicate-string-formatting-argument --msg-template='{path} ({line}): {msg}'" \
#               f" --generated-members=requests.packages.urllib3,requests.codes.ok {file}"
#     assert command == build_pylint_command(file)
#
#
# def test_build_pytest_command():
#     """Build flake8 command"""
#     from demisto_sdk.commands.lint.commands_builder import build_pytest_command
#     command = "pytest -q --junitxml=/devwork/report_pytest.xml"
#     assert command == build_pytest_command()

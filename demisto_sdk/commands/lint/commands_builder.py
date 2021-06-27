# STD python packages
import os
from pathlib import Path
from typing import List, Optional

from demisto_sdk.commands.lint.resources.pylint_plugins.base_checker import \
    base_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.certified_partner_level_checker import \
    cert_partner_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.community_level_checker import \
    community_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.partner_level_checker import \
    partner_msg
from demisto_sdk.commands.lint.resources.pylint_plugins.xsoar_level_checker import \
    xsoar_msg

# Third party packages
# Local imports

excluded_files = ["CommonServerPython.py", "demistomock.py", "CommonServerUserPython.py", "conftest.py", "venv"]


def get_python_exec(py_num: float, is_py2: bool = False) -> str:
    """ Get python executable

    Args:
        py_num(float): Python version X.Y
        is_py2(bool): for python 2 version, Set True if the returned result should have python2 or False for python.

    Returns:
        str: python executable
    """
    if py_num < 3:
        if is_py2:
            py_str = "2"
        else:
            py_str = ""
    else:
        py_str = "3"

    return f"python{py_str}"


def build_flake8_command(files: List[Path], py_num: float) -> str:
    """ Build command for executing flake8 lint check
        https://flake8.pycqa.org/en/latest/user/invocation.html
    Args:
        files(List[Path]): files to execute lint
        py_num(float): The python version in use

    Returns:
        str: flake8 command
    """

    command = f"{get_python_exec(py_num)} -m flake8"
    # Generating file patterns - path1,path2,path3,..
    files_list = [str(file) for file in files]
    command += ' ' + ' '.join(files_list)

    return command


def build_bandit_command(files: List[Path]) -> str:
    """ Build command for executing bandit lint check
        https://github.com/PyCQA/bandit
    Args:
        files(List(Path)):  files to execute lint

    Returns:
        str: bandit command
    """
    command = "python3 -m bandit"
    # Reporting only issues with high and medium severity level
    command += " -ll"
    # Reporting only issues of a high confidence level
    command += " -iii"
    # Skip the following tests: Pickle usage, Use of insecure hash func, Audit url open,
    # Using xml.etree.ElementTree.fromstring,  Using xml.dom.minidom.parseString
    command += " -s B301,B303,B310,B314,B318"
    # Aggregate output by filename
    command += " -a file"
    # File to be excluded when performing lints check
    command += f" --exclude={','.join(excluded_files)}"
    # Only show output in the case of an error
    command += " -q"
    # Setting error format
    command += " --format custom --msg-template '{abspath}:{line}: {test_id} " \
               "[Severity: {severity} Confidence: {confidence}] {msg}'"
    # Generating path patterns - path1,path2,path3,..
    files_list = [str(item) for item in files]
    command += f" -r {','.join(files_list)}"

    return command


def build_xsoar_linter_command(files: List[Path], py_num: float, support_level: str = "base") -> str:
    """ Build command to execute with xsoar linter module
    Args:
        py_num(float): The python version in use
        files(List[Path]): files to execute lint
        support_level: Support level for the file

    Returns:
       str: xsoar linter command using pylint load plugins
    """
    if not support_level:
        support_level = 'base'

    # linters by support level
    support_levels = {
        'base': 'base_checker',
        'community': 'base_checker,community_level_checker',
        'partner': 'base_checker,community_level_checker,partner_level_checker',
        'certified partner': 'base_checker,community_level_checker,partner_level_checker,'
                             'certified_partner_level_checker',
        'xsoar': 'base_checker,community_level_checker,partner_level_checker,certified_partner_level_checker,'
                 'xsoar_level_checker'
    }

    # messages from all level linters
    Msg_XSOAR_linter = {'base_checker': base_msg, 'community_level_checker': community_msg,
                        'partner_level_checker': partner_msg, 'certified_partner_level_checker': cert_partner_msg,
                        'xsoar_level_checker': xsoar_msg}

    checker_path = ""
    message_enable = ""
    if support_levels.get(support_level):
        checkers = support_levels.get(support_level)
        support = checkers.split(',') if checkers else []
        for checker in support:
            checker_path += f"{checker},"
            checker_msgs_list = Msg_XSOAR_linter.get(checker, {}).keys()
            for msg in checker_msgs_list:
                message_enable += f"{msg},"

    command = f"{get_python_exec(py_num, True)} -m pylint"
    # Excluded files
    command += f" --ignore={','.join(excluded_files)}"
    # Disable all errors
    command += " -E --disable=all"
    # Message format
    command += " --msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'"
    # Enable only Demisto Plugins errors.
    command += f" --enable={message_enable}"
    # Load plugins
    if checker_path:
        command += f" --load-plugins {checker_path}"
    # Generating path patterns - file1 file2 file3,..
    files_list = [str(file) for file in files]
    command += " " + " ".join(files_list)
    return command


def build_mypy_command(files: List[Path], version: float) -> str:
    """ Build command to execute with mypy module
        https://mypy.readthedocs.io/en/stable/command_line.html
    Args:
        files(List[Path]): files to execute lint
        version(float): python varsion X.Y (3.7, 2.7 ..)

    Returns:
        str: mypy command
    """
    command = "python3 -m mypy"
    # Define python versions
    command += f" --python-version {version}"
    # This flag enable type checks the body of every function, regardless of whether it has type annotations.
    command += " --check-untyped-defs"
    # This flag makes mypy ignore all missing imports.
    command += " --ignore-missing-imports"
    # This flag adjusts how mypy follows imported modules that were not explicitly passed in via the command line
    command += " --follow-imports=silent"
    # This flag will add column offsets to error messages.
    command += " --show-column-numbers"
    # This flag will precede all errors with “note” messages explaining the context of the error.
    command += " --show-error-codes"
    # Use visually nicer output in error messages
    command += " --pretty"
    # This flag enables redefinion of a variable with an arbitrary type in some contexts.
    command += " --allow-redefinition"
    # Get the full path to the file.
    command += " --show-absolute-path"
    # Disable cache creation
    command += " --cache-dir=/dev/null"
    # Generating path patterns - file1 file2 file3,..
    files_list = [str(item) for item in files]
    command += " " + " ".join(files_list)

    return command


def build_vulture_command(files: List[Path], pack_path: Path, py_num: float) -> str:
    """ Build command to execute with pylint module
        https://github.com/jendrikseipp/vulture
    Args:
        py_num(float): The python version in use
        files(List[Path]): files to execute lint
        pack_path(Path): Package path

    Returns:
       str: vulture command
    """
    command = f"{get_python_exec(py_num)} -m vulture"
    # Excluded files
    command += f" --min-confidence {os.environ.get('VULTURE_MIN_CONFIDENCE_LEVEL', '100')}"
    # File to be excluded when performing lints check
    command += f" --exclude={','.join(excluded_files)}"
    # Whitelist vulture
    whitelist = Path(pack_path) / '.vulture_whitelist.py'
    if whitelist.exists():
        command += f" {whitelist}"
    files_list = [str(item) for item in files]
    command += " " + " ".join(files_list)
    return command


def build_pylint_command(files: List[Path], docker_version: Optional[float] = None) -> str:
    """ Build command to execute with pylint module
        https://docs.pylint.org/en/1.6.0/run.html#invoking-pylint
    Args:
        files(List[Path]): files to execute lint
        docker_version: The version of the python docker image.
    Returns:
       str: pylint command
    """
    command = "python -m pylint"
    # Excluded files
    command += f" --ignore={','.join(excluded_files)}"
    # Prints only errors
    command += " -E"
    # disable xsoar linter messages
    disable = ['bad-option-value']
    # TODO: remove when pylint will update its version to support py3.9
    if docker_version and docker_version >= 3.9:
        disable.append('unsubscriptable-object')
    command += f" --disable={','.join(disable)}"
    # Disable specific errors
    command += " -d duplicate-string-formatting-argument"
    # Message format
    command += " --msg-template='{abspath}:{line}:{column}: {msg_id} {obj}: {msg}'"
    # List of members which are set dynamically and missed by pylint inference system, and so shouldn't trigger
    # E1101 when accessed.
    command += " --generated-members=requests.packages.urllib3,requests.codes.ok"
    # Generating path patterns - file1 file2 file3,..
    files_list = [file.name for file in files]
    command += " " + " ".join(files_list)
    return command


def build_pytest_command(test_xml: str = "", json: bool = False, cov: str = "") -> str:
    """ Build command to execute with pytest module
        https://docs.pytest.org/en/latest/usage.html
    Args:
        test_xml(str): path indicate if required or not
        json(bool): Define json creation after test

    Returns:
        str: pytest command
    """
    command = "python -m pytest -ra -Werror"
    # Generating junit-xml report - used in circle ci
    if test_xml:
        command += " --junitxml=/devwork/report_pytest.xml"
    # Generating json report
    if json:
        command += " --json=/devwork/report_pytest.json"

    if cov:
        command += f' --cov-report= --cov={cov}'

    return command


def build_pwsh_analyze_command(file: Path) -> str:
    """ Build command for powershell analyze

    Args:
        file(Path): files to execute lint

    Returns:
       str: powershell analyze command
    """
    # Invoke script analyzer
    command = "Invoke-ScriptAnalyzer"
    # Return exit code when finished
    command += " -EnableExit"
    # Lint Files paths
    command += f" -Path {file.name}"

    return f"pwsh -Command {command}"


def build_pwsh_test_command() -> str:
    """ Build command for powershell test

    Returns:
       str: powershell test command
    """
    command = "Invoke-Pester"
    # Return exit code when finished
    command += ' -Configuration \'@{Run=@{Exit=$true}; Output=@{Verbosity="Detailed"}}\''

    return f"pwsh -Command {command}"

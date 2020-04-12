import argparse
import glob
import io
import json
import os
import re
import shlex
import sys
from distutils.version import LooseVersion
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen, check_output
from typing import Dict, List, Optional, Tuple, Union

import git
import requests
import urllib3
import yaml
from demisto_sdk.commands.common.constants import (
    CHECKED_TYPES_REGEXES, CONTENT_GITHUB_LINK, DEF_DOCKER, DEF_DOCKER_PWSH,
    PACKAGE_SUPPORTING_DIRECTORIES, PACKAGE_YML_FILE_REGEX,
    PACKS_CHANGELOG_REGEX, PACKS_DIR, PACKS_DIR_REGEX, PACKS_README_FILE_NAME,
    RELEASE_NOTES_REGEX, SDK_API_GITHUB_RELEASES, TYPE_PWSH, UNRELEASE_HEADER)

# disable insecure warnings
urllib3.disable_warnings()


class LOG_COLORS:
    NATIVE = '\033[m'
    RED = '\033[01;31m'
    GREEN = '\033[01;32m'
    YELLOW = '\033[0;33m'


LOG_VERBOSE = False


def set_log_verbose(verbose: bool):
    global LOG_VERBOSE
    LOG_VERBOSE = verbose


def get_log_verbose() -> bool:
    return LOG_VERBOSE


def get_yml_paths_in_dir(project_dir: str, error_msg: str,) -> Tuple[list, str]:
    """
    Gets the project directory and returns the path of the first yml file in that directory
    :param project_dir: string path to the project_dir
    :param error_msg: the error msg to show to the user in case not yml files found in the directory
    :return: first returned argument is the list of all yml files paths in the directory, second returned argument is a
    string path to the first yml file in project_dir
    """
    yml_files = glob.glob(os.path.join(project_dir, '*.yml'))
    if not yml_files:
        if error_msg:
            print(error_msg)
        return [], ''
    return yml_files, yml_files[0]


# print srt in the given color
def print_color(obj, color):
    print(u'{}{}{}'.format(color, obj, LOG_COLORS.NATIVE))


def get_files_in_dir(project_dir: str, file_ending: Tuple[str, str]) -> List[str]:
    """
    Gets the project directory and returns the path of all yml and json files in it
    Args:
        project_dir: string path to the project_dir
        file_ending: list of file endings to search for in given directory
    :return: the path of all yml and json files in it

    """
    files = []
    if project_dir.endswith(file_ending):
        return [project_dir]
    for file_type in file_ending:
        files.extend([f for f in glob.glob(project_dir + '/**/*.' + file_type, recursive=True)])
    return files


def print_error(error_str):
    print_color(error_str, LOG_COLORS.RED)


def print_warning(warning_str):
    print_color(warning_str, LOG_COLORS.YELLOW)


def print_success(success_str):
    print_color(success_str, LOG_COLORS.GREEN)


def run_command(command, is_silenced=True, exit_on_error=True, cwd=None):
    """Run a bash command in the shell.

    Args:
        command (string): The string of the command you want to execute.
        is_silenced (bool): Whether to print command output.
        exit_on_error (bool): Whether to exit on command error.
        cwd (str): the path to the current working directory.

    Returns:
        string. The output of the command you are trying to execute.
    """
    if is_silenced:
        p = Popen(command.split(), stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=cwd)
    else:
        p = Popen(command.split(), cwd=cwd)

    output, err = p.communicate()
    if err:
        if exit_on_error:
            print_error('Failed to run command {}\nerror details:\n{}'.format(command, err))
            sys.exit(1)
        else:
            raise RuntimeError('Failed to run command {}\nerror details:\n{}'.format(command, err))

    return output


def get_remote_file(full_file_path, tag='master'):
    # 'origin/' prefix is used to compared with remote branches but it is not a part of the github url.
    tag = tag.lstrip('origin/')

    # The replace in the end is for Windows support
    github_path = os.path.join(CONTENT_GITHUB_LINK, tag, full_file_path).replace('\\', '/')
    try:
        res = requests.get(github_path, verify=False, timeout=10)
        res.raise_for_status()
    except Exception as exc:
        print_warning('Could not find the old entity file under "{}".\n'
                      'please make sure that you did not break backward compatibility. '
                      'Reason: {}'.format(github_path, exc))
        return {}

    if full_file_path.endswith('json'):
        details = json.loads(res.content)
    elif full_file_path.endswith('yml'):
        details = yaml.safe_load(res.content)
    # if neither yml nor json then probably a CHANGELOG or README file.
    else:
        details = {}
    return details


def filter_packagify_changes(modified_files, added_files, removed_files, tag='master'):
    """
    Mark scripts/integrations that were removed and added as modifiied.

    :param modified_files: list of modified files in branch
    :param added_files: list of new files in branch
    :param removed_files: list of removed files in branch
    :param tag: tag of compared revision

    :return: tuple of updated lists: (modified_files, updated_added_files, removed_files)
    """
    # map IDs to removed files
    packagify_diff = {}  # type: dict
    for file_path in removed_files:
        if file_path.split("/")[0] in PACKAGE_SUPPORTING_DIRECTORIES:
            if PACKS_README_FILE_NAME in file_path:
                continue
            details = get_remote_file(file_path, tag)
            if details:
                uniq_identifier = '_'.join([
                    details['name'],
                    details.get('fromversion', '0.0.0'),
                    details.get('toversion', '99.99.99')
                ])
                packagify_diff[uniq_identifier] = file_path

    updated_added_files = set()
    for file_path in added_files:
        if file_path.split("/")[0] in PACKAGE_SUPPORTING_DIRECTORIES:
            if PACKS_README_FILE_NAME in file_path:
                updated_added_files.add(file_path)
                continue
            with open(file_path) as f:
                details = yaml.safe_load(f.read())

            uniq_identifier = '_'.join([
                details['name'],
                details.get('fromversion', '0.0.0'),
                details.get('toversion', '99.99.99')
            ])
            if uniq_identifier in packagify_diff:
                # if name appears as added and removed, this is packagify process - treat as modified.
                removed_files.remove(packagify_diff[uniq_identifier])
                modified_files.add((packagify_diff[uniq_identifier], file_path))
                continue

        updated_added_files.add(file_path)

    # remove files that are marked as both "added" and "modified"
    for file_path in modified_files:
        if isinstance(file_path, tuple):
            updated_added_files -= {file_path[1]}
        else:
            updated_added_files -= {file_path}

    return modified_files, updated_added_files, removed_files


def get_child_directories(directory):
    """Return a list of paths of immediate child directories of the 'directory' argument"""
    if not os.path.isdir(directory):
        return []
    child_directories = [
        os.path.join(directory, path) for
        path in os.listdir(directory) if os.path.isdir(os.path.join(directory, path))
    ]
    return child_directories


def get_child_files(directory):
    """Return a list of paths of immediate child files of the 'directory' argument"""
    if not os.path.isdir(directory):
        return []
    child_files = [
        os.path.join(directory, path) for
        path in os.listdir(directory) if os.path.isfile(os.path.join(directory, path))
    ]
    return child_files


def get_last_remote_release_version():
    """
    Get latest release tag from remote github page

    :return: tag
    """
    if not os.environ.get('DEMISTO_SDK_SKIP_VERSION_CHECK') and not os.environ.get('CI'):
        try:
            releases_request = requests.get(SDK_API_GITHUB_RELEASES, verify=False, timeout=5)
            releases_request.raise_for_status()
            releases = releases_request.json()
            if isinstance(releases, list) and isinstance(releases[0], dict):
                latest_release = releases[0].get('tag_name')
                if isinstance(latest_release, str):
                    # remove v prefix
                    return latest_release[1:]
        except Exception as exc:
            exc_msg = str(exc)
            if isinstance(exc, requests.exceptions.ConnectionError):
                exc_msg = f'{exc_msg[exc_msg.find(">") + 3:-3]}.\nThis may happen if you are not connected to the internet.'
            print_warning(f'Could not get latest demisto-sdk version.\nEncountered error: {exc_msg}')
    return ''


def get_file(method, file_path, type_of_file):
    data_dictionary = None
    with open(os.path.expanduser(file_path), mode="r", encoding="utf8") as f:
        if file_path.endswith(type_of_file):
            read_file = f.read()
            replaced = read_file.replace("simple: =", "simple: '='")
            # revert str to stream for loader
            stream = io.StringIO(replaced)
            try:
                data_dictionary = method(stream)
            except Exception as e:
                print_error(
                    "{} has a structure issue of file type{}. Error was: {}".format(file_path, type_of_file, str(e)))
                return []
    if type(data_dictionary) is dict:
        return data_dictionary
    return {}


def get_yaml(file_path):
    return get_file(yaml.safe_load, file_path, ('yml', 'yaml'))


def get_json(file_path):
    return get_file(json.load, file_path, 'json')


def get_script_or_integration_id(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        commonfields = data_dictionary.get('commonfields', {})
        return commonfields.get('id', ['-', ])


def collect_ids(file_path):
    """Collect id mentioned in file_path"""
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        return data_dictionary.get('id', '-')


def get_from_version(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        from_version = data_dictionary.get('fromversion', '0.0.0')
        if from_version == "":
            return "0.0.0"

        if not re.match(r"^\d{1,2}\.\d{1,2}\.\d{1,2}$", from_version):
            raise ValueError("{} fromversion is invalid \"{}\". "
                             "Should be of format: \"x.x.x\". for example: \"4.5.0\"".format(file_path, from_version))

        return from_version

    return '0.0.0'


def get_to_version(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        to_version = data_dictionary.get('toversion', '99.99.99')
        if not re.match(r"^\d{1,2}\.\d{1,2}\.\d{1,2}$", to_version):
            raise ValueError("{} toversion is invalid \"{}\". "
                             "Should be of format: \"x.x.x\". for example: \"4.5.0\"".format(file_path, to_version))

        return to_version

    return '99.99.99'


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True

    if v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False

    raise argparse.ArgumentTypeError('Boolean value expected.')


def get_release_notes_file_path(file_path):
    dir_name = os.path.dirname(file_path)

    # CHANGELOG in pack sub dirs
    if re.match(PACKAGE_YML_FILE_REGEX, file_path):
        return os.path.join(dir_name, 'CHANGELOG.md')

    # CHANGELOG in pack root
    if re.match(PACKS_CHANGELOG_REGEX, file_path):
        return file_path

    # outside of packages, change log file will include the original file name.
    file_name = os.path.basename(file_path)
    return os.path.join(dir_name, os.path.splitext(file_name)[0] + '_CHANGELOG.md')


def get_latest_release_notes_text(rn_path):
    if not os.path.isfile(rn_path):
        # releaseNotes were not provided
        return None

    with open(rn_path) as f:
        rn = f.read()

    if not rn:
        # empty releaseNotes is not supported
        return None

    new_rn = re.findall(RELEASE_NOTES_REGEX, rn)
    if new_rn:
        # get release notes up to release header
        new_rn = new_rn[0].rstrip()
    else:
        new_rn = rn.replace(UNRELEASE_HEADER, '')

    return new_rn if new_rn else None


def checked_type(file_path, compared_regexes=None, return_regex=False):
    compared_regexes = compared_regexes or CHECKED_TYPES_REGEXES
    for regex in compared_regexes:
        if re.match(regex, file_path, re.IGNORECASE):
            if return_regex:
                return regex
            return True
    return False


def server_version_compare(v1, v2):
    """compare Demisto versions

    Args:
        v1 (string): string representing Demisto version (first comparable)
        v2 (string): string representing Demisto version (second comparable)


    Returns:
        int.
        0 for equal versions.
        positive if v1 later version than v2.
        negative if v2 later version than v1.
    """

    _v1, _v2 = LooseVersion(v1), LooseVersion(v2)
    if _v1 == _v2:
        return 0
    if _v1 > _v2:
        return 1
    return -1


def run_threads_list(threads_list):
    """
    Start a list of threads and wait for completion (join)

    Arguments:
        threads_list (list of threads) -- list of threads to start and wait for join
    """
    # run each command in a separate thread
    for t in threads_list:
        t.start()
    # wait for the commands to complete
    for t in threads_list:
        t.join()


def get_dockerimage45(script_object):
    """Get the docker image used up to 4.5 (including).

    Arguments:
        script_object {dict} -- [script object containing the dockerimage configuration]
    """
    if 'dockerimage45' in script_object:
        return script_object['dockerimage45']
    return script_object.get('dockerimage', '')


def is_file_path_in_pack(file_path):
    return bool(re.findall(PACKS_DIR_REGEX, file_path))


def get_pack_name(file_path):
    match = re.search(r'^(?:./)?{}/([^/]+)/'.format(PACKS_DIR), file_path)
    return match.group(1) if match else None


def pack_name_to_path(pack_name):
    return os.path.join(PACKS_DIR, pack_name)


def get_matching_regex(string_to_match, regexes):
    # type: (str, Union[list, str]) -> Optional[str]
    """Gets a string and find id the regexes list matches the string. if do, return regex else None.

    Args:
        string_to_match: String to find matching regex
        regexes: regexes to check.

    Returns:
        matching regex if exists, else None
    """
    return checked_type(string_to_match, regexes, return_regex=True)


def get_all_docker_images(script_obj) -> List[str]:
    """Gets a yml as dict and returns a list of all 'dockerimage' values in the yml.

    Args:
        script_obj (dict): A yml dict.

    Returns:
        List. A list of all docker images.
    """
    # this makes sure the first docker in the list is the main docker image.
    def_docker_image = DEF_DOCKER
    if script_obj.get('type') == TYPE_PWSH:
        def_docker_image = DEF_DOCKER_PWSH
    imgs = [script_obj.get('dockerimage') or def_docker_image]

    # get additional docker images
    for key in script_obj.keys():
        if 'dockerimage' in key and key != 'dockerimage':
            if isinstance(script_obj.get(key), str):
                imgs.append(script_obj.get(key))

            elif isinstance(script_obj.get(key), list):
                imgs.extend(script_obj.get(key))

    return imgs


def get_python_version(docker_image, log_verbose=None, no_prints=False):
    """
    Get the python version of a docker image
    Arguments:
        docker_image {string} -- Docker image being used by the project
    Return:
        python version as a float (2.7, 3.7)
    Raises:
        ValueError -- if version is not supported
    """
    if log_verbose is None:
        log_verbose = LOG_VERBOSE
    stderr_out = None if log_verbose else DEVNULL
    py_ver = check_output(["docker", "run", "--rm", docker_image,
                           "python", "-c",
                           "import sys;print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))"],
                          universal_newlines=True, stderr=stderr_out).strip()
    if not no_prints:
        print("Detected python version: [{}] for docker image: {}".format(py_ver, docker_image))

    py_num = float(py_ver)
    if py_num < 2.7 or (3 < py_num < 3.4):  # pylint can only work on python 3.4 and up
        raise ValueError("Python vesion for docker image: {} is not supported: {}. "
                         "We only support python 2.7.* and python3 >= 3.4.".format(docker_image, py_num))
    return py_num


def get_pipenv_dir(py_version, envs_dirs_base):
    """
    Get the direcotry holding pipenv files for the specified python version
    Arguments:
        py_version {float} -- python version as 2.7 or 3.7
    Returns:
        string -- full path to the pipenv dir
    """
    return "{}{}".format(envs_dirs_base, int(py_version))


def print_v(msg, log_verbose=None):
    if log_verbose is None:
        log_verbose = LOG_VERBOSE
    if log_verbose:
        print(msg)


def get_dev_requirements(py_version, envs_dirs_base):
    """
    Get the requirements for the specified py version.

    Arguments:
        py_version {float} -- python version as float (2.7, 3.7)

    Raises:
        ValueError -- If can't detect python version

    Returns:
        string -- requirement required for the project
    """
    env_dir = get_pipenv_dir(py_version, envs_dirs_base)
    stderr_out = None if LOG_VERBOSE else DEVNULL
    requirements = check_output(['pipenv', 'lock', '-r', '-d'], cwd=env_dir, universal_newlines=True,
                                stderr=stderr_out)
    print_v("dev requirements:\n{}".format(requirements))
    return requirements


def get_dict_from_file(path: str) -> Tuple[Dict, Union[str, None]]:
    """
    Get a dict representing the file

    Arguments:
        path - a path to the file

    Returns:
        dict representation of the file, and the file_type, either .yml ot .json
    """
    if path:
        if path.endswith('.yml'):
            return get_yaml(path), 'yml'
        elif path.endswith('.json'):
            return get_json(path), 'json'
    return {}, None


def find_type(path: str):
    """
    returns the content file type

    Arguments:
        path - a path to the file

    Returns:
        string representing the content file type
    """
    _dict, file_type = get_dict_from_file(path)
    if file_type == 'yml':
        if 'category' in _dict:
            return 'integration'
        elif 'script' in _dict:
            return 'script'
        elif 'tasks' in _dict:
            return 'playbook'

    elif file_type == 'json':
        if 'widgetType' in _dict:
            return 'widget'
        elif 'reportType' in _dict:
            return 'report'
        elif 'preProcessingScript' in _dict:
            return 'incidenttype'
        elif 'regex' in _dict:
            return 'reputation'
        elif 'mapping' in _dict or 'unclassifiedCases' in _dict:
            return 'classifier'
        elif 'layout' in _dict or 'kind' in _dict:
            if 'kind' in _dict or 'typeId' in _dict:
                return 'layout'
            else:
                return 'dashboard'

        elif 'id' in _dict:
            _id = _dict['id'].lower()
            if _id.startswith('incident'):
                return 'incidentfield'
            elif _id.startswith('indicator'):
                return 'indicatorfield'

    return ''


def get_common_server_path(env_dir):
    common_server_dir = get_common_server_dir(env_dir)
    return os.path.join(common_server_dir, 'CommonServerPython.py')


def get_common_server_path_pwsh(env_dir):
    common_server_dir = get_common_server_dir_pwsh(env_dir)
    return os.path.join(common_server_dir, 'CommonServerPowerShell.ps1')


def _get_common_server_dir_general(env_dir, name):
    common_server_pack_path = os.path.join(env_dir, 'Packs', 'Base', 'Scripts', name)

    return common_server_pack_path


def get_common_server_dir(env_dir):
    return _get_common_server_dir_general(env_dir, 'CommonServerPython')


def get_common_server_dir_pwsh(env_dir):
    return _get_common_server_dir_general(env_dir, 'CommonServerPowerShell')


def get_content_path() -> str:
    """ Get abs content path, from any CWD
    Returns:
        str: Absolute content path
    """
    git_repo = ""
    try:
        git_repo = git.Repo(os.getcwd(),
                            search_parent_directories=True)
        if 'content' not in git_repo.remote().urls.__next__():
            raise git.InvalidGitRepositoryError
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        print_error("Please run demisto-sdk in content repository - Aborting!")

    return git_repo.working_dir


def run_command_os(command: str, cwd: Path, env: dict = os.environ) -> Tuple[str, str, int]:
    """ Run command in subprocess tty
    Args:
        command(str): Command to be executed.
        cwd(Path): Path from pathlib object to be executed
        env: Enviorment variables for the execution
    Returns:
        str: Stdout of the command
        str: Stderr of the command
        int: exit code of command
    """
    try:
        process = Popen(shlex.split(command),
                        cwd=cwd,
                        env=env,
                        stdout=PIPE,
                        stderr=PIPE,
                        universal_newlines=True)
        stdout, stderr = process.communicate()
    except OSError as e:
        return '', str(e), 1

    return stdout, stderr, process.returncode


def pascal_case(st: str) -> str:
    """Convert a string to pascal case. Will simply remove spaces and make sure the first
    character is capitalized

    Arguments:
        st {str} -- string to convert

    Returns:
        str -- converted string
    """
    words = re.findall(r'[a-zA-Z0-9]+', st)
    return ''.join(''.join([w[0].upper(), w[1:]]) for w in words)


def get_last_release_version():
    """
    Get latest release tag (xx.xx.xx)

    :return: tag
    """
    tags = run_command('git tag').split('\n')
    tags = [tag for tag in tags if re.match(r'\d+\.\d+\.\d+', tag) is not None]
    tags.sort(key=LooseVersion, reverse=True)

    return tags[0]


def is_file_from_content_repo(file_path: str) -> Tuple[bool, str]:
    """ Chech if an absolute file_path is part of content repo.
    Args:
        file_path (str): The file path which is checked.
    Returns:
        bool: if file is part of content repo.
        str: relative path of file in content repo.
    """
    git_repo = git.Repo(os.getcwd(),
                        search_parent_directories=True)
    if 'content' not in git_repo.remote().urls.__next__():
        return False, ''
    content_path_parts = Path(git_repo.working_dir).parts
    input_path_parts = Path(file_path).parts
    input_path_parts_prefix = input_path_parts[:len(content_path_parts)]
    if content_path_parts == input_path_parts_prefix:
        return True, '/'.join(input_path_parts[len(content_path_parts):])
    else:
        return False, ''

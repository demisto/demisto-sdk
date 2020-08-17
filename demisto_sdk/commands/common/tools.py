import argparse
import glob
import io
import json
import os
import re
import shlex
import sys
from distutils.version import LooseVersion
from functools import partial
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen, check_output
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

import click
import colorama
import git
import requests
import urllib3
import yaml
from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, CHECKED_TYPES_REGEXES,
    CLASSIFIERS_DIR, CONTENT_GITHUB_LINK, CONTENT_GITHUB_ORIGIN,
    CONTENT_GITHUB_UPSTREAM, DASHBOARDS_DIR, DEF_DOCKER, DEF_DOCKER_PWSH,
    ID_IN_COMMONFIELDS, ID_IN_ROOT, INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR, INTEGRATIONS_DIR, JSON_ALL_INDICATOR_TYPES_REGEXES,
    LAYOUTS_DIR, PACKAGE_SUPPORTING_DIRECTORIES, PACKAGE_YML_FILE_REGEX,
    PACKS_DIR, PACKS_DIR_REGEX, PACKS_README_FILE_NAME, PLAYBOOKS_DIR,
    RELEASE_NOTES_DIR, RELEASE_NOTES_REGEX, REPORTS_DIR, SCRIPTS_DIR,
    SDK_API_GITHUB_RELEASES, TEST_PLAYBOOKS_DIR, TYPE_PWSH, UNRELEASE_HEADER,
    WIDGETS_DIR, FileType)
from ruamel.yaml import YAML

# disable insecure warnings
urllib3.disable_warnings()

# inialize color palette
colorama.init()

ryaml = YAML()
ryaml.preserve_quotes = True
ryaml.allow_duplicate_keys = True


class LOG_COLORS:
    NATIVE = colorama.Style.RESET_ALL
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    WHITE = colorama.Fore.WHITE


LOG_VERBOSE = False

LAYOUT_CONTAINER_FIELDS = {'details', 'detailsV2', 'edit', 'close', 'mobile', 'quickView', 'indicatorsQuickView',
                           'indicatorsDetails'}


def set_log_verbose(verbose: bool):
    global LOG_VERBOSE
    LOG_VERBOSE = verbose


def get_log_verbose() -> bool:
    return LOG_VERBOSE


def get_yml_paths_in_dir(project_dir: str, error_msg: str = '') -> Tuple[list, str]:
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


def get_files_in_dir(project_dir: str, file_endings: list, recursive: bool = True) -> list:
    """
    Gets the project directory and returns the path of all yml, json and py files in it
    Args:
        project_dir: String path to the project_dir
        file_endings: List of file endings to search for in a given directory
        recursive: Indicates whether search should be recursive or not
    :return: The path of files with file_endings in the current dir
    """
    files = []
    pattern: str = '/**/*.' if recursive else '/*.'
    for file_type in file_endings:
        if project_dir.endswith(file_type):
            return [project_dir]
        files.extend([f for f in glob.glob(project_dir + pattern + file_type, recursive=recursive)])
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


def get_remote_file(full_file_path, tag='master', return_content=False):
    """
    Args:
        full_file_path (string):The full path of the file.
        tag (string): The branch name. default is 'master'
        return_content (bool): Determines whether to return the file's raw content or the dict representation of it.
    Returns:
        The file content in the required format.

    """
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
    if return_content:
        return res.content
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


def has_remote_configured():
    """
    Checks to see if a remote named "upstream" is configured. This is important for forked
    repositories as it will allow validation against the demisto/content master branch as
    opposed to the master branch of the fork.
    :return: bool : True if remote is configured, False if not.
    """
    remotes = run_command('git remote -v')
    if re.search(CONTENT_GITHUB_UPSTREAM, remotes):
        return True
    else:
        return False


def is_origin_content_repo():
    """
    Checks to see if a remote named "origin" is configured. This check helps to determine if
    validation needs to be ran against the origin master branch or the upstream master branch
    :return: bool : True if remote is configured, False if not.
    """
    remotes = run_command('git remote -v')
    if re.search(CONTENT_GITHUB_ORIGIN, remotes):
        return True
    else:
        return False


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
                exc_msg = f'{exc_msg[exc_msg.find(">") + 3:-3]}.\n' \
                          f'This may happen if you are not connected to the internet.'
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
                return {}
    if type(data_dictionary) is dict:
        return data_dictionary
    return {}


def get_yaml(file_path):
    return get_file(yaml.safe_load, file_path, ('yml', 'yaml'))


def get_ryaml(file_path: str) -> dict:
    """
    Get yml file contents using ruaml

    Args:
        file_path (string): The file path

    Returns:
        dict. The yml contents
    """
    try:
        with open(os.path.expanduser(file_path), 'r') as yf:
            data = ryaml.load(yf)
    except FileNotFoundError as e:
        click.echo(f'File {file_path} not found. Error was: {str(e)}', nl=True)
    except Exception as e:
        click.echo(
            "{} has a structure issue of file type yml. Error was: {}".format(file_path, str(e)), nl=True)
    return data


def get_json(file_path):
    return get_file(json.load, file_path, 'json')


def get_script_or_integration_id(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        commonfields = data_dictionary.get('commonfields', {})
        return commonfields.get('id', ['-', ])


def get_entity_id_by_entity_type(data: dict, content_entity: str):
    """
    Returns the id of the content entity given its entity type
    :param data: The data of the file
    :param content_entity: The content entity type
    :return: The file id
    """
    if content_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
        return data.get('commonfields', {}).get('id', '')
    elif content_entity == LAYOUTS_DIR:
        return data.get('typeId', '')
    else:
        return data.get('id', '')


def get_entity_name_by_entity_type(data: dict, content_entity: str):
    """
    Returns the name of the content entity given its entity type
    :param data: The data of the file
    :param content_entity: The content entity type
    :return: The file name
    """
    if content_entity == LAYOUTS_DIR:
        return data.get('typeId', '')
    else:
        return data.get('name', '')


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


def old_get_release_notes_file_path(file_path):
    dir_name = os.path.dirname(file_path)

    # CHANGELOG in pack sub dirs
    if re.match(PACKAGE_YML_FILE_REGEX, file_path):
        return os.path.join(dir_name, 'CHANGELOG.md')

    # We got the CHANGELOG file to get its release notes
    if file_path.endswith('CHANGELOG.md'):
        return file_path

    # outside of packages, change log file will include the original file name.
    file_name = os.path.basename(file_path)
    return os.path.join(dir_name, os.path.splitext(file_name)[0] + '_CHANGELOG.md')


def old_get_latest_release_notes_text(rn_path):
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


def get_release_notes_file_path(file_path):
    """
    Accepts file path which is alleged to contain release notes. Validates that the naming convention
    is followed. If the file identified does not match the naming convention, error is returned.
    :param file_path: str - File path of the suspected release note.
    :return: file_path: str - Validated release notes path.
    """
    if file_path is None:
        print_warning("Release notes were not found.")
        return None
    else:
        if bool(re.search(r'\d{1,2}_\d{1,2}_\d{1,2}\.md', file_path)):
            return file_path
        else:
            print_warning(f'Unsupported file type found in ReleaseNotes directory - {file_path}')
            return None


def get_latest_release_notes_text(rn_path):
    if rn_path is None:
        print_warning('Path to release notes not found.')
        rn = None
    else:
        with open(rn_path) as f:
            rn = f.read()

        if not rn:
            print_error(f'Release Notes may not be empty. Please fill out correctly. - {rn_path}')
            return None

    return rn if rn else None


def checked_type(file_path, compared_regexes=None, return_regex=False):
    compared_regexes = compared_regexes or CHECKED_TYPES_REGEXES
    for regex in compared_regexes:
        if re.search(regex, file_path, re.IGNORECASE):
            if return_regex:
                return regex
            return True
    return False


def format_version(version):
    """format server version to form X.X.X

    Args:
        version (string): string representing Demisto version

    Returns:
        string.
        The formatted server version.
    """
    formatted_version = version
    if len(version.split('.')) == 1:
        formatted_version = f'{version}.0.0'
    elif len(version.split('.')) == 2:
        formatted_version = f'{version}.0'

    return formatted_version


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

    v1 = format_version(v1)
    v2 = format_version(v2)

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


def is_file_path_in_pack(file_path):
    return bool(re.findall(PACKS_DIR_REGEX, file_path))


def get_pack_name(file_path):
    """
    extract pack name (folder name) from file path

    Arguments:
        file_path (str): path of a file inside the pack

    Returns:
        pack name (str)
    """
    # the regex extracts pack name from relative paths, for example: Packs/EWSv2 -> EWSv2
    match = re.search(rf'^{PACKS_DIR_REGEX}[/\\]([^/\\]+)[/\\]?', file_path)
    return match.group(1) if match else None


def get_pack_names_from_files(file_paths, skip_file_types=None):
    if skip_file_types is None:
        skip_file_types = set()

    packs = set()
    for path in file_paths:
        # renamed files are in a tuples - the second element is the new file name
        if isinstance(path, tuple):
            path = path[1]

        file_type = find_type(path)
        if file_type not in skip_file_types:
            pack = get_pack_name(path)
            if pack and is_file_path_in_pack(path):
                packs.add(pack)

    return packs


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


def get_dict_from_file(path: str, use_ryaml: bool = False) -> Tuple[Dict, Union[str, None]]:
    """
    Get a dict representing the file

    Arguments:
        path - a path to the file
        use_ryaml - Whether to use ryaml for file loading or not

    Returns:
        dict representation of the file, and the file_type, either .yml ot .json
    """
    if path:
        if path.endswith('.yml'):
            if use_ryaml:
                return get_ryaml(path), 'yml'
            return get_yaml(path), 'yml'
        elif path.endswith('.json'):
            return get_json(path), 'json'
        elif path.endswith('.py'):
            return {}, 'py'
    return {}, None


def find_type(path: str = '', _dict=None, file_type: Optional[str] = None, ignore_sub_categories: bool = False):  # noqa: C901
    """
    returns the content file type

    Arguments:
        path - a path to the file

    Returns:
        string representing the content file type
    """
    if path.endswith('.md'):
        if 'README' in path:
            return FileType.README

        if RELEASE_NOTES_DIR in path:
            return FileType.RELEASE_NOTES

        if 'description' in path:
            return FileType.DESCRIPTION

        return FileType.CHANGELOG

    if path.endswith('.png'):
        return FileType.IMAGE

    if not _dict and not file_type:
        _dict, file_type = get_dict_from_file(path)

    if file_type == 'py':
        return FileType.PYTHON_FILE

    if file_type == 'yml':
        if 'category' in _dict:
            if 'beta' in _dict and not ignore_sub_categories:
                return FileType.BETA_INTEGRATION

            return FileType.INTEGRATION

        if 'script' in _dict:
            if TEST_PLAYBOOKS_DIR in path and not ignore_sub_categories:
                return FileType.TEST_SCRIPT

            return FileType.SCRIPT

        if 'tasks' in _dict:
            if TEST_PLAYBOOKS_DIR in path:
                return FileType.TEST_PLAYBOOK

            return FileType.PLAYBOOK

    if file_type == 'json':
        if 'widgetType' in _dict:
            return FileType.WIDGET

        if 'orientation' in _dict:
            return FileType.REPORT

        if 'preProcessingScript' in _dict:
            return FileType.INCIDENT_TYPE

        if 'regex' in _dict or checked_type(path, JSON_ALL_INDICATOR_TYPES_REGEXES):
            return FileType.REPUTATION

        if 'brandName' in _dict and 'transformer' in _dict:
            return FileType.OLD_CLASSIFIER

        if 'transformer' in _dict and 'keyTypeMap' in _dict:
            return FileType.CLASSIFIER

        if 'canvasContextConnections' in _dict:
            return FileType.CONNECTION

        if 'mapping' in _dict:
            return FileType.MAPPER

        if 'layout' in _dict or 'kind' in _dict:
            if 'kind' in _dict or 'typeId' in _dict:
                return FileType.LAYOUT

            return FileType.DASHBOARD

        if 'group' in _dict and LAYOUT_CONTAINER_FIELDS.intersection(_dict):
            return FileType.LAYOUTS_CONTAINER

        # When using it for all files validation- sometimes 'id' can be integer
        if 'id' in _dict:
            if isinstance(_dict['id'], str):
                _id = _dict['id'].lower()
                if _id.startswith('incident'):
                    return FileType.INCIDENT_FIELD
                if _id.startswith('indicator'):
                    return FileType.INDICATOR_FIELD
            else:
                print(f'The file {path} could not be recognized, please update the "id" to be a string')

    return None


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


def is_external_repository():
    """
    Returns True if script executed from private repository

    """
    git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
    private_settings_path = os.path.join(git_repo.working_dir, '.private-repo-settings')
    return os.path.exists(private_settings_path)


def get_content_path() -> str:
    """ Get abs content path, from any CWD
    Returns:
        str: Absolute content path
    """
    try:
        git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
        remote_url = git_repo.remote().urls.__next__()
        is_fork_repo = 'content' in remote_url
        is_external_repo = is_external_repository()

        if not is_fork_repo and not is_external_repo:
            raise git.InvalidGitRepositoryError
        return git_repo.working_dir
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        print_error("Please run demisto-sdk in content repository - Aborting!")
    return ''


def run_command_os(command: str, cwd: Union[Path, str], env: Union[os._Environ, dict] = os.environ) -> \
        Tuple[str, str, int]:
    """ Run command in subprocess tty
    Args:
        command(str): Command to be executed.
        cwd(Path): Path from pathlib object to be executed
        env: Environment variables for the execution
    Returns:
        str: Stdout of the command
        str: Stderr of the command
        int: exit code of command
    """
    if isinstance(cwd, str):
        cwd = Path(cwd)
    try:
        process = Popen(
            shlex.split(command),
            cwd=cwd,
            env=env,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True
        )
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


def capital_case(st: str) -> str:
    """Capitalize the first letter of each word of a string. The remaining characters are untouched.

    Arguments:
        st {str} -- string to convert

    Returns:
        str -- converted string
    """
    if len(st) >= 1:
        words = st.split()
        return ' '.join([f'{s[:1].upper()}{s[1:]}' for s in words if len(s) >= 1])
    else:
        return ''


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
    """ Check if an absolute file_path is part of content repo.
    Args:
        file_path (str): The file path which is checked.
    Returns:
        bool: if file is part of content repo.
        str: relative path of file in content repo.
    """
    git_repo = git.Repo(os.getcwd(),
                        search_parent_directories=True)
    remote_url = git_repo.remote().urls.__next__()
    is_fork_repo = 'content' in remote_url
    is_external_repo = is_external_repository()

    if not is_fork_repo and not is_external_repo:
        return False, ''
    content_path_parts = Path(git_repo.working_dir).parts
    input_path_parts = Path(file_path).parts
    input_path_parts_prefix = input_path_parts[:len(content_path_parts)]
    if content_path_parts == input_path_parts_prefix:
        return True, '/'.join(input_path_parts[len(content_path_parts):])
    else:
        return False, ''


def should_file_skip_validation(file_path: str) -> bool:
    """Check if the file cannot be validated under 'run_all_validations_on_file' method for various reasons,
        either if it's a test file, or if it's a file that's been validated somewhere else
        Args:
            file_path (str): The file path which is checked.
        Returns:
            bool: True if the file's validation should be skipped, False otherwise.
        """
    file_extension = os.path.splitext(file_path)[-1]
    # We validate only yml json and .md files
    if file_extension not in ['.yml', '.json', '.md']:
        return True
    if any(ignore_pattern in file_path.lower() for ignore_pattern in ALL_FILES_VALIDATION_IGNORE_WHITELIST):
        return True
    # Ignoring changelog and description files since these are checked on the integration validation
    if 'changelog' in file_path.lower() or 'description' in file_path.lower():
        return True
    # unified files should not be validated
    if file_path.endswith('_unified.yml'):
        return True
    return False


def retrieve_file_ending(file_path: str) -> str:
    """
    Retrieves the file ending (without the dot)
    :param file_path: The file path
    :return: The file ending
    """
    os_split: tuple = os.path.splitext(file_path)
    if os_split:
        file_ending: str = os_split[1]
        if file_ending and '.' in file_ending:
            return file_ending[1:]
    return ''


def get_depth(data: Any) -> int:
    """
    Returns the depth of a data object
    :param data: The data
    :return: The depth of the data object
    """
    if data and isinstance(data, dict):
        return 1 + max(get_depth(data[key]) for key in data)
    if data and isinstance(data, list):
        return 1 + max(get_depth(element) for element in data)
    return 0


def is_test_config_match(test_config: dict, test_playbook_id: str = '', integration_id: str = '') -> bool:
    """
    Given a test configuration from conf.json file, this method checks if the configuration is configured for the
    test playbook or for integration_id.
    Since in conf.json there could be test configurations with 'integrations' as strings or list of strings
    the type of test_configurations['integrations'] is checked in first and the match according to the type.
    If file type is not an integration- will return True if the test_playbook id matches playbookID.
    Args:
        test_config: A test configuration from conf.json file under 'tests' key.
        test_playbook_id: A test playbook ID.
        integration_id: An integration ID.
    If both test_playbook_id and integration_id are given will look for a match of both, else will look for match
    of either test playbook id or integration id
    Returns:
        True if the test configuration contains the test playbook and the content item or False if not
    """
    test_playbook_match = test_playbook_id == test_config.get('playbookID')
    test_integrations = test_config.get('integrations')
    if isinstance(test_integrations, list):
        integration_match = any(
            test_integration for test_integration in test_integrations if test_integration == integration_id)
    else:
        integration_match = test_integrations == integration_id
    # If both playbook id and integration id are given
    if integration_id and test_playbook_id:
        return test_playbook_match and integration_match

    # If only integration id is given
    if integration_id:
        return integration_match

    # If only test playbook is given
    if test_playbook_id:
        return test_playbook_match

    return False


def get_not_registered_tests(conf_json_tests: list, content_item_id: str, file_type: str, test_playbooks: list) -> list:
    """
    Return all test playbooks that are not configured in conf.json file
    Args:
        conf_json_tests: the 'tests' value of 'conf.json file
        content_item_id: A content item ID, could be a script, an integration or a playbook.
        file_type: The file type, could be an integration or a playbook.
        test_playbooks: The yml file's list of test playbooks

    Returns:
        A list of TestPlaybooks not configured
    """
    not_registered_tests = []
    for test in test_playbooks:
        if file_type == 'playbook':
            test_registered_in_conf_json = any(
                test_config for test_config in conf_json_tests if is_test_config_match(test_config,
                                                                                       test_playbook_id=test)
            )
        else:
            test_registered_in_conf_json = any(
                test_config for test_config in conf_json_tests if is_test_config_match(test_config,
                                                                                       integration_id=content_item_id)
            )
        if not test_registered_in_conf_json:
            not_registered_tests.append(test)
    return not_registered_tests


def _get_file_id(file_type: str, file_content: Dict):
    """
    Gets the ID of a content item according to it's type
    Args:
        file_type: The type of the content item
        file_content: The content of the content item

    Returns:
        The file's content ID
    """
    file_id = ''
    if file_type in ID_IN_ROOT:
        file_id = file_content.get('id', '')
    elif file_type in ID_IN_COMMONFIELDS:
        file_id = file_content.get('commonfields', {}).get('id')
    return file_id


def is_path_of_integration_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == INTEGRATIONS_DIR


def is_path_of_script_directory(path: str) -> bool:
    """Returns true if directory is script directory false if not.
    """
    return os.path.basename(path) == SCRIPTS_DIR


def is_path_of_playbook_directory(path: str) -> bool:
    """Returns true if directory is playbook directory false if not.
    """
    return os.path.basename(path) == PLAYBOOKS_DIR


def is_path_of_test_playbook_directory(path: str) -> bool:
    """Returns true if directory is test_playbook directory false if not.
    """
    return os.path.basename(path) == TEST_PLAYBOOKS_DIR


def is_path_of_report_directory(path: str) -> bool:
    """Returns true if directory is report directory false if not.
    """
    return os.path.basename(path) == REPORTS_DIR


def is_path_of_dashboard_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == DASHBOARDS_DIR


def is_path_of_widget_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == WIDGETS_DIR


def is_path_of_incident_field_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == INCIDENT_FIELDS_DIR


def is_path_of_incident_type_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == INCIDENT_TYPES_DIR


def is_path_of_indicator_field_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == INDICATOR_FIELDS_DIR


def is_path_of_layout_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == LAYOUTS_DIR


def is_path_of_classifier_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == CLASSIFIERS_DIR


def get_parent_directory_name(path: str) -> str:
    """
    Retrieves the parent directory name
    :param path: path to get the parent dir om
    :return: parent directory nme
    """
    return os.path.basename(os.path.dirname(os.path.abspath(path)))


def get_content_file_type_dump(file_path: str) -> Callable[[str], str]:
    """
    Return a method with which 'curr' (the current key the lies in the path of the error) should be printed with
    If the file is a yml file:
        will return a yaml.dump function
    If the file is a json file:
        will return a json.dumps function configured with indent=4
    In any other case- will just print the string representation of the key.

    The file type is checked according to the file extension

    Args:
        file_path: The file path whose type is determined in this method

    Returns:
        A function that returns string representation of 'curr'
    """
    # Setting the method that should the curr path
    file_extension = os.path.splitext(file_path)[-1]
    curr_string_transformer: Union[partial[str], Type[str], Callable] = str
    if file_extension in ['.yml', '.yaml']:
        curr_string_transformer = yaml.dump
    elif file_extension == '.json':
        curr_string_transformer = partial(json.dumps, indent=4)
    return curr_string_transformer


def get_code_lang(file_data: dict, file_entity: str) -> str:
    """
    Returns the code language by the file entity
    :param file_data: The file data
    :param file_entity: The file entity
    :return: The code language
    """
    if file_entity == INTEGRATIONS_DIR:
        return file_data.get('script', {}).get('type', '')
    elif file_entity == SCRIPTS_DIR:
        return file_data.get('type', {})
    return ''


def get_content_release_identifier(branch_name: str) -> Optional[str]:
    """

    Args:
        branch_name: the branch name to get config.yml from

    Returns:
        GIT_SHA1 of latest content release if successfully returned from content repo.
        else None.
    """
    try:
        file_content = get_remote_file('.circleci/config.yml', tag=branch_name)
    except Exception:
        return None
    else:
        return file_content.get('references', {}).get('environment', {}).get('environment', {}).get('GIT_SHA1')


def camel_to_snake(camel: str) -> str:
    """
    Converts camel case (CamelCase) strings to snake case (snake_case) strings.
    Args:
        camel (str): The camel case string.

    Returns:
        str: The snake case string.
    """
    camel_to_snake_pattern = re.compile(r'(?<!^)(?=[A-Z][a-z])')
    snake = camel_to_snake_pattern.sub('_', camel).lower()
    return snake

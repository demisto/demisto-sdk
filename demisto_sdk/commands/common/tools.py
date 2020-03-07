import re
import os
import sys
import json
import glob
import argparse
from subprocess import Popen, PIPE, DEVNULL, check_output
from distutils.version import LooseVersion
from typing import Union, Optional, Tuple

import urllib3
import yaml
import requests

from demisto_sdk.commands.common.constants import CHECKED_TYPES_REGEXES, PACKAGE_SUPPORTING_DIRECTORIES,\
    CONTENT_GITHUB_LINK, PACKAGE_YML_FILE_REGEX, UNRELEASE_HEADER, RELEASE_NOTES_REGEX, PACKS_DIR, PACKS_DIR_REGEX,\
    DEF_DOCKER

# disable insecure warnings
urllib3.disable_warnings()


class LOG_COLORS:
    NATIVE = '\033[m'
    RED = '\033[01;31m'
    GREEN = '\033[01;32m'
    YELLOW = '\033[0;33m'


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
def print_color(str, color):
    print(color + str + LOG_COLORS.NATIVE)


def print_error(error_str):
    print_color(error_str, LOG_COLORS.RED)


def print_warning(warning_str):
    print_color(warning_str, LOG_COLORS.YELLOW)


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
        res = requests.get(github_path, verify=False)
        res.raise_for_status()
    except Exception as exc:
        print_warning('Could not find the old entity file under "{}".\n'
                      'please make sure that you did not break backward compatibility. '
                      'Reason: {}'.format(github_path, exc))
        return {}

    if full_file_path.endswith('json'):
        details = json.loads(res.content)
    else:
        details = yaml.safe_load(res.content)

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


def get_last_release_version():
    """
    Get latest release tag (xx.xx.xx)

    :return: tag
    """
    tags = run_command('git tag').split('\n')
    tags = [tag for tag in tags if re.match(r'\d+\.\d+\.\d+', tag) is not None]
    tags.sort(key=LooseVersion, reverse=True)

    return tags[0]


def get_file(method, file_path, type_of_file):
    data_dictionary = None
    with open(os.path.expanduser(file_path), "r") as f:
        if file_path.endswith(type_of_file):
            try:
                data_dictionary = method(f)
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

    if re.match(PACKAGE_YML_FILE_REGEX, file_path):
        return os.path.join(dir_name, 'CHANGELOG.md')

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


def get_docker_images(script_obj):
    imgs = [script_obj.get('dockerimage') or DEF_DOCKER]
    alt_imgs = script_obj.get('alt_dockerimages')
    if alt_imgs:
        imgs.extend(alt_imgs)
    return imgs


def get_all_docker_images(script_obj):
    """Gets a yml as dict and returns a list of all 'dockerimage' values in the yml.

    Args:
        script_obj (dict): A yml dict.

    Returns:
        List. A list of all docker images.
    """
    # this makes sure the first docker in the list is the main docker image.
    imgs = [script_obj.get('dockerimage') or DEF_DOCKER]

    # get additional docker images
    for key in script_obj.keys():
        if 'dockerimage' in key and key != 'dockerimage':
            if isinstance(script_obj.get(key), str):
                imgs.append(script_obj.get(key))

            elif isinstance(script_obj.get(key), list):
                imgs.extend(script_obj.get(key))

    return imgs


def get_python_version(docker_image, log_verbose, no_prints=False):
    """
    Get the python version of a docker image
    Arguments:
        docker_image {string} -- Docker image being used by the project
    Return:
        python version as a float (2.7, 3.7)
    Raises:
        ValueError -- if version is not supported
    """
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


def print_v(msg, log_verbose=False):
    if log_verbose:
        print(msg)


def get_dev_requirements(py_version, envs_dirs_base, log_verbose=False):
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
    stderr_out = None if log_verbose else DEVNULL
    requirements = check_output(['pipenv', 'lock', '-r', '-d'], cwd=env_dir, universal_newlines=True,
                                stderr=stderr_out)
    print_v("dev requirements:\n{}".format(requirements))
    return requirements

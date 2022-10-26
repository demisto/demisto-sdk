import argparse
import glob
import io
import logging
import os
import re
import shlex
import sys
import urllib.parse
from collections import OrderedDict
from concurrent.futures import as_completed
from configparser import ConfigParser, MissingSectionHeaderError
from contextlib import contextmanager
from distutils.version import LooseVersion
from enum import Enum
from functools import lru_cache
from pathlib import Path, PosixPath
from subprocess import DEVNULL, PIPE, Popen, check_output
from time import sleep
from typing import Callable, Dict, List, Match, Optional, Set, Tuple, Union

import click
import colorama
import demisto_client
import git
import giturlparse
import requests
import urllib3
from packaging.version import parse
from pebble import ProcessFuture, ProcessPool
from requests.exceptions import HTTPError

from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST, API_MODULES_PACK, CLASSIFIERS_DIR,
    DASHBOARDS_DIR, DEF_DOCKER, DEF_DOCKER_PWSH,
    DEFAULT_CONTENT_ITEM_FROM_VERSION, DEFAULT_CONTENT_ITEM_TO_VERSION,
    DOC_FILES_DIR, ENV_DEMISTO_SDK_MARKETPLACE, ID_IN_COMMONFIELDS, ID_IN_ROOT,
    INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR, INTEGRATIONS_DIR, JOBS_DIR, LAYOUTS_DIR, LISTS_DIR,
    MARKETPLACE_KEY_PACK_METADATA, METADATA_FILE_NAME, MODELING_RULES_DIR,
    NON_LETTERS_OR_NUMBERS_PATTERN, OFFICIAL_CONTENT_ID_SET_PATH,
    PACK_METADATA_IRON_BANK_TAG, PACKAGE_SUPPORTING_DIRECTORIES,
    PACKAGE_YML_FILE_REGEX, PACKS_DIR, PACKS_DIR_REGEX,
    PACKS_PACK_IGNORE_FILE_NAME, PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME, PARSING_RULES_DIR, PLAYBOOKS_DIR,
    PRE_PROCESS_RULES_DIR, RELEASE_NOTES_DIR, RELEASE_NOTES_REGEX, REPORTS_DIR,
    SCRIPTS_DIR, SIEM_ONLY_ENTITIES, TEST_PLAYBOOKS_DIR, TRIGGER_DIR,
    TYPE_PWSH, UNRELEASE_HEADER, UUID_REGEX, WIDGETS_DIR, XDRC_TEMPLATE_DIR,
    XSIAM_DASHBOARDS_DIR, XSIAM_REPORTS_DIR, XSOAR_CONFIG_FILE, FileType,
    FileTypeToIDSetKeys, IdSetKeys, MarketplaceVersions, urljoin)
from demisto_sdk.commands.common.git_content_config import (GitContentConfig,
                                                            GitProvider)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler

json = JSON_Handler()

logger = logging.getLogger("demisto-sdk")
yaml = YAML_Handler()

urllib3.disable_warnings()

# initialize color palette
colorama.init()


class LOG_COLORS:
    NATIVE = colorama.Style.RESET_ALL
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    WHITE = colorama.Fore.WHITE


class TagParser:
    def __init__(self, tag_prefix: str, tag_suffix: str, remove_tag_text: bool = True):
        self._tag_prefix = tag_prefix
        self._tag_suffix = tag_suffix
        self._pattern = re.compile(fr'{tag_prefix}((.|\s)+?){tag_suffix}')
        self._remove_tag_text = remove_tag_text

    def parse(self, text: str, remove_tag: Optional[bool] = None) -> str:
        """
        Given a prefix and suffix of an expected tag, remove the tag and the text it's wrapping, or just the wrappers
        Args:
            text (str): text that may contain given tags.
            remove_tag (bool): overrides remove_tag_text value. Determines whether to remove the tag

        Returns:
            Text with no wrapper tags.
        """
        if text and 0 <= text.find(self._tag_prefix) < text.find(self._tag_suffix):
            remove_tag = remove_tag if isinstance(remove_tag, bool) else self._remove_tag_text
            # collect {orignal_text: text_to_replace}
            matches = re.finditer(self._pattern, text)
            replace_map = {}
            for match in matches:
                replace_val = '' if remove_tag else match.group(1)
                replace_map[re.escape(match.group())] = replace_val

            # replace collected text->replacement
            pattern = re.compile("|".join(replace_map.keys()))
            text = pattern.sub(lambda m: replace_map[re.escape(m.group(0))], text)
        return text


class MarketplaceTagParser:
    XSOAR_PREFIX = '<~XSOAR>\n'
    XSOAR_SUFFIX = '\n</~XSOAR>\n'
    XSOAR_INLINE_PREFIX = '<~XSOAR>'
    XSOAR_INLINE_SUFFIX = '</~XSOAR>'
    XSIAM_PREFIX = '<~XSIAM>\n'
    XSIAM_SUFFIX = '\n</~XSIAM>\n'
    XSIAM_INLINE_PREFIX = '<~XSIAM>'
    XSIAM_INLINE_SUFFIX = '</~XSIAM>'

    def __init__(self, marketplace: str = MarketplaceVersions.XSOAR.value):
        self.marketplace = marketplace
        self._xsoar_parser = TagParser(
            tag_prefix=self.XSOAR_PREFIX,
            tag_suffix=self.XSOAR_SUFFIX,
        )
        self._xsoar_inline_parser = TagParser(
            tag_prefix=self.XSOAR_INLINE_PREFIX,
            tag_suffix=self.XSOAR_INLINE_SUFFIX,
        )
        self._xsiam_parser = TagParser(
            tag_prefix=self.XSIAM_PREFIX,
            tag_suffix=self.XSIAM_SUFFIX,
        )
        self._xsiam_inline_parser = TagParser(
            tag_prefix=self.XSIAM_INLINE_PREFIX,
            tag_suffix=self.XSIAM_INLINE_SUFFIX,
        )

    @property
    def marketplace(self):
        return self._marketplace

    @marketplace.setter
    def marketplace(self, marketplace):
        self._marketplace = marketplace
        self._should_remove_xsoar_text = marketplace != MarketplaceVersions.XSOAR.value
        self._should_remove_xsiam_text = marketplace != MarketplaceVersions.MarketplaceV2.value

    def parse_text(self, text):
        # the order of parse is important. inline should always be checked after paragraph tag
        # xsoar->xsoar_inline->xsiam->xsiam_inline
        return self._xsiam_inline_parser.parse(
            remove_tag=self._should_remove_xsiam_text,
            text=self._xsiam_parser.parse(
                remove_tag=self._should_remove_xsiam_text,
                text=self._xsoar_inline_parser.parse(
                    remove_tag=self._should_remove_xsoar_text,
                    text=self._xsoar_parser.parse(
                        remove_tag=self._should_remove_xsoar_text,
                        text=text,
                    ),
                ),
            ),
        )


MARKETPLACE_TAG_PARSER = None

LOG_VERBOSE = False

LAYOUT_CONTAINER_FIELDS = {'details', 'detailsV2', 'edit', 'close', 'mobile', 'quickView', 'indicatorsQuickView',
                           'indicatorsDetails'}
SDK_PYPI_VERSION = r'https://pypi.org/pypi/demisto-sdk/json'

SUFFIX_TO_REMOVE = ('_dev', '_copy')


def generate_xsiam_normalized_name(file_name, prefix):
    if file_name.startswith(f'external-{prefix}-'):
        return file_name
    elif file_name.startswith(f'{prefix}-'):
        return file_name.replace(f'{prefix}-', f'external-{prefix}-')
    else:
        return f'external-{prefix}-{file_name}'


def set_log_verbose(verbose: bool):
    global LOG_VERBOSE
    LOG_VERBOSE = verbose


def get_log_verbose() -> bool:
    return LOG_VERBOSE


def get_mp_tag_parser():
    global MARKETPLACE_TAG_PARSER
    if MARKETPLACE_TAG_PARSER is None:
        MARKETPLACE_TAG_PARSER = MarketplaceTagParser(
            os.getenv(ENV_DEMISTO_SDK_MARKETPLACE, MarketplaceVersions.XSOAR.value))
    return MARKETPLACE_TAG_PARSER


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
    project_path = Path(project_dir)
    glob_function = project_path.rglob if recursive else project_path.glob
    for file_type in file_endings:
        if project_dir.endswith(file_type):
            return [project_dir]
        files.extend([str(f) for f in glob_function(f'*.{file_type}')])
    return files


def src_root() -> Path:
    """ Demisto-sdk absolute path from src root.

    Returns:
        Path: src root path.
    """
    git_dir = git.Repo(Path.cwd(),
                       search_parent_directories=True).working_tree_dir

    return Path(git_dir) / 'demisto_sdk'


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
        p = Popen(command.split(), cwd=cwd)  # type: ignore

    output, err = p.communicate()
    if err:
        if exit_on_error:
            print_error('Failed to run command {}\nerror details:\n{}'.format(command, err))
            sys.exit(1)
        else:
            raise RuntimeError('Failed to run command {}\nerror details:\n{}'.format(command, err))

    return output


core_pack_list: Optional[
    list] = None  # Initiated in get_core_pack_list function. Here to create a "cached" core_pack_list


@lru_cache(maxsize=128)
def get_core_pack_list() -> list:
    """Getting the core pack list from Github content

    Returns:
        Core pack list
    """
    global core_pack_list
    if isinstance(core_pack_list, list):
        return core_pack_list
    if not is_external_repository():
        core_pack_list = get_remote_file(
            'Tests/Marketplace/core_packs_list.json',
            git_content_config=GitContentConfig(repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME,
                                                git_provider=GitProvider.GitHub)
        ) or []
        core_pack_list.extend(get_remote_file(
            'Tests/Marketplace/core_packs_mpv2_list.json',
            git_content_config=GitContentConfig(repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME,
                                                git_provider=GitProvider.GitHub)
        ) or [])
        core_pack_list = list(set(core_pack_list))
    else:
        # no core packs in external repos.
        core_pack_list = []
    return core_pack_list


def get_local_remote_file(
        full_file_path: str,
        tag: str = 'master',
        return_content: bool = False,
):
    repo = git.Repo(search_parent_directories=True)  # the full file path could be a git file path
    repo_git_util = GitUtil(repo)
    git_path = repo_git_util.get_local_remote_file_path(full_file_path, tag)
    file_content = repo_git_util.get_local_remote_file_content(git_path)
    if return_content:
        return file_content.encode()
    return get_file_details(file_content, full_file_path)


def get_remote_file_from_api(
        full_file_path: str,
        git_content_config: Optional[GitContentConfig],
        tag: str = 'master',
        return_content: bool = False,
        suppress_print: bool = False,
):
    if not git_content_config:
        git_content_config = GitContentConfig()
    if git_content_config.git_provider == GitProvider.GitLab:
        full_file_path_quote_plus = urllib.parse.quote_plus(full_file_path)
        git_path = urljoin(git_content_config.base_api, 'files', full_file_path_quote_plus, 'raw')
    else:  # github
        git_path = urljoin(git_content_config.base_api, tag, full_file_path)

    github_token: Optional[str] = None
    gitlab_token: Optional[str] = None
    try:
        github_token = git_content_config.CREDENTIALS.github_token
        gitlab_token = git_content_config.CREDENTIALS.gitlab_token
        if git_content_config.git_provider == GitProvider.GitLab:
            res = requests.get(git_path,
                               params={'ref': tag},
                               headers={'PRIVATE-TOKEN': gitlab_token},
                               verify=False)
            res.raise_for_status()
        else:  # Github
            res = requests.get(git_path, verify=False, timeout=10, headers={
                'Authorization': f"Bearer {github_token}" if github_token else None,
                'Accept': f'application/vnd.github.VERSION.raw',
            })  # Sometime we need headers
            if not res.ok:  # sometime we need param token
                res = requests.get(
                    git_path,
                    verify=False,
                    timeout=10,
                    params={'token': github_token}
                )

        res.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # Replace token secret if needed
        err_msg: str = str(exc).replace(github_token, 'XXX') if github_token else str(exc)
        err_msg = err_msg.replace(gitlab_token, 'XXX') if gitlab_token else err_msg
        if not suppress_print:
            if is_external_repository():
                click.secho(
                    f'You are working in a private repository: "{git_content_config.current_repository}".\n'
                    f'The github/gitlab token in your environment is undefined.\n'
                    f'Getting file from local repository instead. \n'
                    f'If you wish to get the file from the remote repository, \n'
                    f'Please define your github or gitlab token in your environment.\n'
                    f'`export {GitContentConfig.CREDENTIALS.ENV_GITHUB_TOKEN_NAME}=<TOKEN> or`\n'
                    f'export {GitContentConfig.CREDENTIALS.ENV_GITLAB_TOKEN_NAME}=<TOKEN>', fg='yellow'
                )

            click.secho(
                f'Could not find the old entity file under "{git_path}".\n'
                'please make sure that you did not break backward compatibility.\n'
                f'Reason: {err_msg}', fg='yellow'
            )
        return {}
    file_content = res.content
    if return_content:
        return file_content
    return get_file_details(file_content, full_file_path)


def get_file_details(
        file_content,
        full_file_path: str,
) -> Dict:
    if full_file_path.endswith('json'):
        file_details = json.loads(file_content)
    elif full_file_path.endswith('yml'):
        file_details = yaml.load(file_content)
    # if neither yml nor json then probably a CHANGELOG or README file.
    else:
        file_details = {}
    return file_details


@lru_cache(maxsize=128)
def get_remote_file(
        full_file_path: str,
        tag: str = 'master',
        return_content: bool = False,
        suppress_print: bool = False,
        git_content_config: Optional[GitContentConfig] = None,
):
    """
    Args:
        full_file_path:The full path of the file.
        tag: The branch name. default is 'master'
        return_content: Determines whether to return the file's raw content or the dict representation of it.
        suppress_print: whether to suppress the warning message in case the file was not found.
        git_content_config: The content config to take the file from
    Returns:
        The file content in the required format.

    """
    tag = tag.replace('origin/', '').replace('demisto/', '')
    if not git_content_config:
        try:
            return get_local_remote_file(full_file_path, tag, return_content)
        except Exception as e:
            if not suppress_print:
                click.secho(f"Could not get local remote file because of: {str(e)}\n"
                            f"Searching the remote file content with the API.")
    return get_remote_file_from_api(full_file_path, git_content_config, tag, return_content, suppress_print)


def filter_files_on_pack(pack: str, file_paths_list=str()) -> set:
    """
    filter_files_changes_on_pack.

    :param file_paths_list: list of content files
    :param pack: pack to filter

    :return: files_paths_on_pack: set of file paths contains only files located in the given pack
    """
    files_paths_on_pack = set()
    for file in file_paths_list:
        if get_pack_name(file) == pack:
            files_paths_on_pack.add(file)

    return files_paths_on_pack


def filter_packagify_changes(modified_files, added_files, removed_files, tag='master'):
    """
    Mark scripts/integrations that were removed and added as modified.

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
                    details.get('fromversion', DEFAULT_CONTENT_ITEM_FROM_VERSION),
                    details.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)
                ])
                packagify_diff[uniq_identifier] = file_path

    updated_added_files = set()
    for file_path in added_files:
        if file_path.split("/")[0] in PACKAGE_SUPPORTING_DIRECTORIES:
            if PACKS_README_FILE_NAME in file_path:
                updated_added_files.add(file_path)
                continue
            with open(file_path) as f:
                details = yaml.load(f)

            uniq_identifier = '_'.join([
                details['name'],
                details.get('fromversion', DEFAULT_CONTENT_ITEM_FROM_VERSION),
                details.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)
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
    if re.search(GitContentConfig.CONTENT_GITHUB_UPSTREAM, remotes):
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
    if re.search(GitContentConfig.CONTENT_GITHUB_ORIGIN, remotes):
        return True
    else:
        return False


def get_last_remote_release_version():
    """
    Get latest release tag from PYPI.

    :return: tag
    """
    if not os.environ.get(
            'CI'):  # Check only when no on CI. If you want to disable it - use `DEMISTO_SDK_SKIP_VERSION_CHECK` environment variable
        try:
            pypi_request = requests.get(SDK_PYPI_VERSION, verify=False, timeout=5)
            pypi_request.raise_for_status()
            pypi_json = pypi_request.json()
            version = pypi_json.get('info', {}).get('version', '')
            return version
        except Exception as exc:
            exc_msg = str(exc)
            if isinstance(exc, requests.exceptions.ConnectionError):
                exc_msg = f'{exc_msg[exc_msg.find(">") + 3:-3]}.\n' \
                          f'This may happen if you are not connected to the internet.'
            print_warning(f'Could not get latest demisto-sdk version.\nEncountered error: {exc_msg}')

    return ''


@lru_cache()
def get_file(file_path, type_of_file, clear_cache=False):
    if clear_cache:
        get_file.cache_clear()
    file_path = Path(file_path).absolute()
    data_dictionary = None
    with file_path.open(mode='r', encoding='utf8') as f:
        if type_of_file in file_path.suffix:
            read_file = f.read()
            replaced = re.sub(r"(simple: \s*\n*)(=)(\s*\n)", r'\1"\2"\3', read_file)
            # revert str to stream for loader
            stream = io.StringIO(replaced)
            try:
                if type_of_file in ('yml', '.yml'):
                    data_dictionary = yaml.load(stream)

                else:
                    data_dictionary = json.load(stream)

            except Exception as e:
                raise ValueError(
                    "{} has a structure issue of file type {}. Error was: {}".format(file_path, type_of_file, str(e)))
    if isinstance(data_dictionary, (dict, list)):
        return data_dictionary
    return {}


def get_yaml(file_path, cache_clear=False):
    return get_file(file_path, 'yml', clear_cache=cache_clear)


def get_json(file_path, cache_clear=False):
    if cache_clear:
        get_file.cache_clear()
    return get_file(file_path, 'json', clear_cache=cache_clear)


def get_script_or_integration_id(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        commonfields = data_dictionary.get('commonfields', {})
        return commonfields.get('id', ['-', ])


def get_api_module_integrations_set(changed_api_modules: Set, integration_set: Set):
    integrations_set = list()
    for integration in integration_set:
        integration_data = list(integration.values())[0]
        if changed_api_modules & set(integration_data.get('api_modules', [])):
            integrations_set.append(integration_data)
    return integrations_set


def get_api_module_ids(file_list) -> Set:
    """Extracts APIModule IDs from the file list"""
    api_module_set = set()
    if file_list:
        for pf in file_list:
            parent = pf
            while f'/{API_MODULES_PACK}/Scripts/' in parent:
                parent = get_parent_directory_name(parent, abs_path=True)
                if f'/{API_MODULES_PACK}/Scripts/' in parent:
                    pf = parent
            if parent != pf:
                api_module_set.add(os.path.basename(pf))
    return api_module_set


def get_entity_id_by_entity_type(data: dict, content_entity: str):
    """
    Returns the id of the content entity given its entity type
    :param data: The data of the file
    :param content_entity: The content entity type
    :return: The file id
    """
    try:
        if content_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
            return data.get('commonfields', {}).get('id', '')
        elif content_entity == LAYOUTS_DIR:
            return data.get('typeId', '')
        else:
            return data.get('id', '')

    except AttributeError:
        raise ValueError(f"Could not retrieve id from file of type {content_entity} - make sure the file structure is "
                         f"valid")


def get_entity_name_by_entity_type(data: dict, content_entity: str):
    """
    Returns the name of the content entity given its entity type
    :param data: The data of the file
    :param content_entity: The content entity type
    :return: The file name
    """
    try:
        if content_entity == LAYOUTS_DIR:
            if 'typeId' in data:
                return data.get('typeId', '')
            return data.get('name', '')  # for layoutscontainer
        return data.get('name', '')

    except AttributeError:
        raise ValueError(
            f"Could not retrieve name from file of type {content_entity} - make sure the file structure is "
            f"valid")


def collect_ids(file_path):
    """Collect id mentioned in file_path"""
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        return data_dictionary.get('id', '-')


def get_from_version(file_path):
    data_dictionary = get_yaml(file_path) if file_path.endswith('yml') else get_json(file_path)

    if data_dictionary:
        from_version = data_dictionary.get('fromversion') if 'fromversion' in data_dictionary \
            else data_dictionary.get('fromVersion', '')

        if not from_version:
            logging.warning(f'fromversion/fromVersion was not found in {data_dictionary.get("id", "")}')
            return ''

        if not re.match(r'^\d{1,2}\.\d{1,2}\.\d{1,2}$', from_version):
            raise ValueError(f'{file_path} fromversion is invalid "{from_version}". '
                             'Should be of format: "x.x.x". for example: "4.5.0"')

        return from_version

    return ''


def get_to_version(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        to_version = data_dictionary.get('toversion', DEFAULT_CONTENT_ITEM_TO_VERSION)
        if not re.match(r'^\d{1,2}\.\d{1,2}\.\d{1,2}$', to_version):
            raise ValueError(f'{file_path} toversion is invalid "{to_version}". '
                             'Should be of format: "x.x.x". for example: "4.5.0"')

        return to_version

    return DEFAULT_CONTENT_ITEM_TO_VERSION


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True

    if v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False

    raise argparse.ArgumentTypeError('Boolean value expected.')


def to_dict(obj):
    if isinstance(obj, Enum):
        return obj.name

    if not hasattr(obj, '__dict__'):
        return obj

    result = {}
    for key, val in obj.__dict__.items():
        if key.startswith("_"):
            continue

        element = []
        if isinstance(val, list):
            for item in val:
                element.append(to_dict(item))
        else:
            element = to_dict(val)
        result[key] = element

    return result


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
        new_rn = rn.replace(UNRELEASE_HEADER, '')  # type: ignore

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
        try:
            with open(rn_path) as f:
                rn = f.read()

            if not rn:
                print_error(f'Release Notes may not be empty. Please fill out correctly. - {rn_path}')
                return None
        except IOError:
            return ''

    return rn if rn else None


def format_version(version):
    """format server version to form X.X.X

    Args:
        version (string): string representing Demisto version

    Returns:
        string.
        The formatted server version.
    """
    formatted_version = version
    if not version:
        formatted_version = '0.0.0'
    elif len(version.split('.')) == 1:
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


def get_max_version(versions: List[str]) -> str:
    """get max version between Demisto versions.

    Args:
        versions (list): list of strings representing Demisto version.

    Returns:
        str.
        max version.
    """

    if len(versions) == 0:
        raise BaseException("Error: empty versions list")
    max_version = versions[0]
    for version in versions[1:]:
        if server_version_compare(version, max_version) == 1:
            max_version = version
    return max_version


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


def add_default_pack_known_words(file_path):
    """
    Ignores the pack's content:
    1. Pack's name.
    2. Integrations name.
    3. Integrations command names'.
    4. Scripts name.

    Note: please add to this function any further ignores in the future.
    Args:
        file_path: RN file path

    Returns: A list of all the Pack's content the doc_reviewer should ignore.

    """
    default_pack_known_words = [get_pack_name(file_path), ]
    default_pack_known_words.extend(get_integration_name_and_command_names(file_path))
    default_pack_known_words.extend(get_scripts_names(file_path))
    return default_pack_known_words


def get_integration_name_and_command_names(file_path):
    """
    1. Get the RN file path.
    2. Check if integrations exist in the current pack.
    3. For each integration, load the yml file.
    3. Keep in a set all the commands names.
    4. Keep in a set all the integrations names.
    Args:
        file_path: RN file path

    Returns: (set) of all the commands and integrations names found.

    """
    integrations_dir_path = os.path.join(PACKS_DIR, get_pack_name(file_path), INTEGRATIONS_DIR)
    command_names: Set[str] = set()
    if not glob.glob(integrations_dir_path):
        return command_names

    found_integrations: List[str] = os.listdir(integrations_dir_path)
    if found_integrations:
        for integration in found_integrations:
            command_names.add(integration)

            integration_path_full = os.path.join(integrations_dir_path, integration, f'{integration}.yml')
            yml_dict = get_yaml(integration_path_full)
            commands = yml_dict.get("script", {}).get('commands', [])
            command_names = command_names.union({command.get('name') for command in commands})

    return command_names


def get_scripts_names(file_path):
    """
    1. Get the RN file path
    2. Check if scripts exist in the current pack
    3. Keep in a set all the scripts names
    Args:
        file_path: RN file path

    Returns: (set) of all the scripts names found.

    """
    scripts_dir_path = os.path.join(PACKS_DIR, get_pack_name(file_path), SCRIPTS_DIR)
    scripts_names: Set[str] = set()
    if not glob.glob(scripts_dir_path):
        return scripts_names

    found_scripts: List[str] = os.listdir(scripts_dir_path)
    if found_scripts:
        for script in found_scripts:
            if script.endswith('.md'):
                continue  # in case the script is in the old version of CommonScripts - JS code, ignore the md file
            elif script.endswith('.yml'):
                # in case the script is in the old version of CommonScripts - JS code, only yml exists not in a dir
                script_path_full = os.path.join(scripts_dir_path, script)
            else:
                script_path_full = os.path.join(scripts_dir_path, script, f'{script}.yml')
            try:
                yml_dict = get_yaml(script_path_full)
                scripts_names.add(yml_dict.get("name"))
            except FileNotFoundError:
                # we couldn't load the script as the path is not fit Content convention scripts' names
                scripts_names.add(script)
    return scripts_names


def get_pack_name(file_path):
    """
    extract pack name (folder name) from file path

    Arguments:
        file_path (str): path of a file inside the pack

    Returns:
        pack name (str)
    """
    file_path = Path(file_path)
    parts = file_path.parts
    if 'Packs' not in parts:
        return None
    pack_name_index = parts.index('Packs') + 1
    if len(parts) <= pack_name_index:
        return None
    return parts[pack_name_index]


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


def filter_files_by_type(file_paths=None, skip_file_types=None) -> set:
    """get set of files and return the set whiteout the types to skip

    Args:
    - file_paths (set): set of content files.
    - skip_file_types List[str]: list of file types to skip.

    Returns:
    files (set): list of files whiteout the types to skip
    """
    if file_paths is None:
        file_paths = set()
    files = set()
    for path in file_paths:
        # renamed files are in a tuples - the second element is the new file name
        if isinstance(path, tuple):
            path = path[1]
        file_type = find_type(path)
        if file_type not in skip_file_types and is_file_path_in_pack(path):
            files.add(path)
    return files


def pack_name_to_path(pack_name):
    return os.path.join(get_content_path(), PACKS_DIR, pack_name)


def pack_name_to_posix_path(pack_name):
    return PosixPath(pack_name_to_path(pack_name))


def get_pack_ignore_file_path(pack_name):
    return os.path.join(get_content_path(), PACKS_DIR, pack_name, PACKS_PACK_IGNORE_FILE_NAME)


def get_test_playbook_id(test_playbooks_list: list, tpb_path: str) -> Tuple:  # type: ignore
    """

    Args:
        test_playbooks_list: The test playbook list from id_set
        tpb_path: test playbook path.

    Returns (Tuple): test playbook name and pack.

    """
    for test_playbook_dict in test_playbooks_list:
        test_playbook_id = list(test_playbook_dict.keys())[0]
        test_playbook_path = test_playbook_dict[test_playbook_id].get('file_path')
        test_playbook_pack = test_playbook_dict[test_playbook_id].get('pack')
        if not test_playbook_path or not test_playbook_pack:
            continue

        if tpb_path in test_playbook_path:
            return test_playbook_id, test_playbook_pack
    return None, None


def get_ignore_pack_skipped_tests(pack_name: str, modified_packs: set, id_set: dict) -> set:
    """
    Retrieve the skipped tests of a given pack, as detailed in the .pack-ignore file

    expected ignored tests structure in .pack-ignore:
        [file:playbook-Not-To-Run-Directly.yml]
        ignore=auto-test

    Arguments:
        pack_name (str): name of the pack
        modified_packs (set): Set of modified packs
        id_set (dict): ID set

    Returns:
        ignored_tests_set (set[str]): set of ignored test ids

    """
    if not modified_packs:
        modified_packs = {pack_name}
    ignored_tests_set = set()
    file_name_to_ignore_dict: Dict[str, List[str]] = {}
    test_playbooks = id_set.get('TestPlaybooks', {})

    pack_ignore_path = get_pack_ignore_file_path(pack_name)
    if pack_name in modified_packs:
        if os.path.isfile(pack_ignore_path):
            try:
                # read pack_ignore using ConfigParser
                config = ConfigParser(allow_no_value=True)
                config.read(pack_ignore_path)

                # go over every file in the config
                for section in config.sections():
                    if section.startswith("file:"):
                        # given section is of type file
                        file_name: str = section[5:]
                        for key in config[section]:
                            if key == 'ignore':
                                # group ignore codes to a list
                                file_name_to_ignore_dict[file_name] = str(config[section][key]).split(',')
            except MissingSectionHeaderError:
                pass

    for file_name, ignore_list in file_name_to_ignore_dict.items():
        if any(ignore_code == 'auto-test' for ignore_code in ignore_list):
            test_id, test_pack = get_test_playbook_id(test_playbooks, file_name)
            if test_id:
                ignored_tests_set.add(test_id)
    return ignored_tests_set


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


def get_dict_from_file(path: str,
                       raises_error: bool = True, clear_cache: bool = False) -> Tuple[Dict, Union[str, None]]:
    """
    Get a dict representing the file

    Arguments:
        path - a path to the file
        raises_error - Whether to raise a FileNotFound error if `path` is not a valid file.

    Returns:
        dict representation of the file or of the first item if the file contents are a list with a single dictionary,
        and the file_type, either .yml or .json
    """
    try:
        if path:
            if path.endswith('.yml'):
                return get_yaml(path, cache_clear=clear_cache), 'yml'
            elif path.endswith('.json'):
                res = get_json(path, cache_clear=clear_cache)
                if isinstance(res, list) and len(res) == 1 and isinstance(res[0], dict):
                    return res[0], 'json'
                else:
                    return res, 'json'
            elif path.endswith('.py'):
                return {}, 'py'
            elif path.endswith('.xif'):
                return {}, 'xif'
    except FileNotFoundError as e:
        if raises_error:
            raise

    return {}, None


@lru_cache()
def find_type_by_path(path: Union[str, Path] = '') -> Optional[FileType]:
    """Find FileType value of a path, without accessing the file.
    This function is here as we want to implement lru_cache and we can do it on `find_type`
    as dict is not hashable.

    It's also theoretically faster, as files are not opened.
    """
    path = Path(path)
    if path.suffix == '.md':
        if 'README' in path.name:
            return FileType.README
        elif RELEASE_NOTES_DIR in path.parts:
            return FileType.RELEASE_NOTES
        elif 'description' in path.name:
            return FileType.DESCRIPTION
        elif path.name.endswith('CHANGELOG.md'):
            return FileType.CHANGELOG

    if path.suffix == '.json':
        if RELEASE_NOTES_DIR in path.parts:
            return FileType.RELEASE_NOTES_CONFIG
        elif LISTS_DIR in os.path.dirname(path):
            return FileType.LISTS
        elif path.parent.name == JOBS_DIR:
            return FileType.JOB
        elif INDICATOR_TYPES_DIR in path.parts:
            return FileType.REPUTATION
        elif XSIAM_DASHBOARDS_DIR in path.parts:
            return FileType.XSIAM_DASHBOARD
        elif XSIAM_REPORTS_DIR in path.parts:
            return FileType.XSIAM_REPORT
        elif TRIGGER_DIR in path.parts:
            return FileType.TRIGGER
        elif path.name == METADATA_FILE_NAME:
            return FileType.METADATA
        elif path.name.endswith(XSOAR_CONFIG_FILE):
            return FileType.XSOAR_CONFIG
        elif 'CONTRIBUTORS' in path.name:
            return FileType.CONTRIBUTORS
        elif XDRC_TEMPLATE_DIR in path.parts:
            return FileType.XDRC_TEMPLATE

    elif path.name.endswith('_image.png'):
        if path.name.endswith('Author_image.png'):
            return FileType.AUTHOR_IMAGE
        elif XSIAM_DASHBOARDS_DIR in path.parts:
            return FileType.XSIAM_DASHBOARD_IMAGE
        elif XSIAM_REPORTS_DIR in path.parts:
            return FileType.XSIAM_REPORT_IMAGE
        return FileType.IMAGE

    elif path.suffix == '.png' and DOC_FILES_DIR in path.parts:
        return FileType.DOC_IMAGE

    elif path.suffix == '.ps1':
        return FileType.POWERSHELL_FILE

    elif path.suffix == '.py':
        return FileType.PYTHON_FILE

    elif path.suffix == '.js':
        return FileType.JAVASCRIPT_FILE

    elif path.suffix == '.xif':
        return FileType.XIF_FILE

    elif path.suffix == '.yml':
        if path.parts[0] in {'.circleci', '.gitlab'}:
            return FileType.BUILD_CONFIG_FILE

        elif path.parent.name == SCRIPTS_DIR and path.name.startswith('script-'):
            # Packs/myPack/Scripts/script-myScript.yml
            return FileType.SCRIPT

        elif path.parent.parent.name == SCRIPTS_DIR and path.name == f'{path.parent.name}.yml':
            # Packs/myPack/Scripts/myScript/myScript.yml
            return FileType.SCRIPT

        elif XDRC_TEMPLATE_DIR in path.parts:
            return FileType.XDRC_TEMPLATE_YML

    elif path.name == FileType.PACK_IGNORE:
        return FileType.PACK_IGNORE

    elif path.name == FileType.SECRET_IGNORE:
        return FileType.SECRET_IGNORE

    elif path.parent.name == DOC_FILES_DIR:
        return FileType.DOC_FILE

    return None


# flake8: noqa: C901


def find_type(
        path: str = '',
        _dict=None,
        file_type: Optional[str] = None,
        ignore_sub_categories: bool = False,
        ignore_invalid_schema_file: bool = False,
        clear_cache: bool = False
):
    """
    returns the content file type

    Arguments:
         path (str): a path to the file.
        _dict (dict): file dict representation if exists.
        file_type (str): a string representation of the file type.
        ignore_sub_categories (bool): ignore the sub categories, True to ignore, False otherwise.
        ignore_invalid_schema_file (bool): whether to ignore raising error on invalid schema files,
            True to ignore, False otherwise.
        clear_cache (bool): wether to clear the cache

    Returns:
        FileType: string representing of the content file type, None otherwise.
    """
    type_by_path = find_type_by_path(path)
    if type_by_path:
        return type_by_path
    try:
        if not _dict and not file_type:
            _dict, file_type = get_dict_from_file(path, clear_cache=clear_cache)

    except FileNotFoundError:
        # unable to find the file - hence can't identify it
        return None
    except ValueError as err:
        if ignore_invalid_schema_file:
            # invalid file schema
            logger.debug(str(err))
            return None
        raise err

    if file_type == 'yml' or path.lower().endswith('.yml'):
        if 'category' in _dict:
            if _dict.get('beta') and not ignore_sub_categories:
                return FileType.BETA_INTEGRATION

            return FileType.INTEGRATION

        if 'script' in _dict:
            if TEST_PLAYBOOKS_DIR in Path(path).parts and not ignore_sub_categories:
                return FileType.TEST_SCRIPT

            return FileType.SCRIPT

        if 'tasks' in _dict:
            if TEST_PLAYBOOKS_DIR in Path(path).parts:
                return FileType.TEST_PLAYBOOK

            return FileType.PLAYBOOK

        if 'rules' in _dict:
            if 'samples' in _dict and PARSING_RULES_DIR in Path(path).parts:
                return FileType.PARSING_RULE

            if MODELING_RULES_DIR in Path(path).parts:
                return FileType.MODELING_RULE

        if 'global_rule_id' in _dict:
            return FileType.CORRELATION_RULE

    if file_type == 'json' or path.lower().endswith('.json'):
        if path.lower().endswith('_schema.json'):
            return FileType.MODELING_RULE_SCHEMA

        if 'widgetType' in _dict:
            return FileType.WIDGET

        if 'orientation' in _dict:
            return FileType.REPORT

        if 'color' in _dict and 'cliName' not in _dict:
            if 'definitionId' in _dict and _dict['definitionId'] and \
                    _dict['definitionId'].lower() not in ['incident', 'indicator']:
                return FileType.GENERIC_TYPE
            return FileType.INCIDENT_TYPE

        # 'regex' key can be found in new reputations files while 'reputations' key is for the old reputations
        # located in reputations.json file.
        if 'regex' in _dict or 'reputations' in _dict:
            return FileType.REPUTATION

        if 'brandName' in _dict and 'transformer' in _dict:
            return FileType.OLD_CLASSIFIER

        if ('transformer' in _dict and 'keyTypeMap' in _dict) or 'mapping' in _dict:
            if _dict.get('type') and _dict.get('type') == 'classification':
                return FileType.CLASSIFIER
            elif _dict.get('type') and 'mapping' in _dict.get('type'):
                return FileType.MAPPER
            return None

        if 'canvasContextConnections' in _dict:
            return FileType.CONNECTION

        if 'layout' in _dict or 'kind' in _dict:  # it's a Layout or Dashboard but not a Generic Object
            if 'kind' in _dict or 'typeId' in _dict:
                return FileType.LAYOUT

            return FileType.DASHBOARD

        if 'group' in _dict and LAYOUT_CONTAINER_FIELDS.intersection(_dict):
            return FileType.LAYOUTS_CONTAINER

        if 'scriptName' in _dict and 'existingEventsFilters' in _dict and 'readyExistingEventsFilters' in _dict and \
                'newEventFilters' in _dict and 'readyNewEventFilters' in _dict:
            return FileType.PRE_PROCESS_RULES

        if 'allRead' in _dict and 'truncated' in _dict:
            return FileType.LISTS

        if 'definitionIds' in _dict and 'views' in _dict:
            return FileType.GENERIC_MODULE

        if 'auditable' in _dict:
            return FileType.GENERIC_DEFINITION

        if isinstance(_dict, dict) and {'isAllFeeds', 'selectedFeeds', 'isFeed'}.issubset(_dict.keys()):
            return FileType.JOB

        if isinstance(_dict, dict) and 'wizard' in _dict:
            return FileType.WIZARD

        if 'dashboards_data' in _dict:
            return FileType.XSIAM_DASHBOARD

        if 'templates_data' in _dict:
            return FileType.XSIAM_REPORT

        if 'trigger_id' in _dict:
            return FileType.TRIGGER

        if 'profile_type' in _dict and 'yaml_template' in _dict:
            return FileType.XDRC_TEMPLATE

        # When using it for all files validation- sometimes 'id' can be integer
        if 'id' in _dict:
            if isinstance(_dict['id'], str):
                if 'definitionId' in _dict and _dict['definitionId'] and \
                        _dict['definitionId'].lower() not in ['incident', 'indicator']:
                    return FileType.GENERIC_FIELD
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


def is_external_repository() -> bool:
    """
    Returns True if script executed from private repository

    """
    try:
        git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
        private_settings_path = os.path.join(git_repo.working_dir, '.private-repo-settings')
        return os.path.exists(private_settings_path)
    except git.InvalidGitRepositoryError:
        return True


def get_content_id_set() -> dict:
    """Getting the ID Set from official content's bucket"""
    return requests.get(OFFICIAL_CONTENT_ID_SET_PATH).json()


def get_content_path() -> str:
    """ Get abs content path, from any CWD
    Returns:
        str: Absolute content path
    """
    try:
        if content_path := os.getenv('DEMISTO_SDK_CONTENT_PATH'):
            git_repo = git.Repo(content_path)
            logger.debug(f'Using content path: {content_path}')
        else:
            git_repo = git.Repo(Path.cwd(), search_parent_directories=True)

        remote_url = git_repo.remote().urls.__next__()
        is_fork_repo = 'content' in remote_url
        is_external_repo = is_external_repository()

        if not is_fork_repo and not is_external_repo:
            raise git.InvalidGitRepositoryError
        return git_repo.working_dir
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        print_warning("Please run demisto-sdk in content repository!")
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
    try:
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

    except Exception as e:
        click.secho(f"Unable to identify the repository: {e}")
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
    if file_type in ID_IN_ROOT:
        return file_content.get('id', '')
    elif file_type in ID_IN_COMMONFIELDS:
        return file_content.get('commonfields', {}).get('id')
    return file_content.get('trigger_id', '')


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


def is_path_of_pre_process_rules_directory(path: str) -> bool:
    """Returns true if directory is pre-processing rules directory, false if not.
    """
    return os.path.basename(path) == PRE_PROCESS_RULES_DIR


def is_path_of_lists_directory(path: str) -> bool:
    return os.path.basename(path) == LISTS_DIR


def is_path_of_classifier_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not.
    """
    return os.path.basename(path) == CLASSIFIERS_DIR


def get_parent_directory_name(path: str, abs_path: bool = False) -> str:
    """
    Retrieves the parent directory name
    :param path: path to get the parent dir name
    :param abs_path: when set to true, will return absolute path
    :return: parent directory name
    """
    parent_dir_name = os.path.dirname(os.path.abspath(path))
    if abs_path:
        return parent_dir_name
    return os.path.basename(parent_dir_name)


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


def open_id_set_file(id_set_path):
    id_set = {}
    try:
        with open(id_set_path, 'r') as id_set_file:
            id_set = json.load(id_set_file)
    except IOError:
        print_warning("Could not open id_set file")
        raise
    finally:
        return id_set


def get_demisto_version(client: demisto_client) -> str:
    """
    Args:
        demisto_client: A configured demisto_client instance

    Returns:
        the server version of the Demisto instance.
    """
    try:
        resp = client.generic_request('/about', 'GET')
        about_data = json.loads(resp[0].replace("'", '"'))
        return parse(about_data.get('demistoVersion'))  # type: ignore
    except Exception:
        return "0"


def arg_to_list(arg: Union[str, List[str]], separator: str = ",") -> List[str]:
    """
       Converts a string representation of lists to a python list
       Args:
              arg: string or list of string.
              separator: A string separator to separate the strings, the default is a comma.
       Returns:
             list, contains strings.

    """
    if not arg:
        return []
    if isinstance(arg, list):
        return arg
    if isinstance(arg, str):
        if arg[0] == '[' and arg[-1] == ']':
            return json.loads(arg)
        return [s.strip() for s in arg.split(separator)]
    return [arg]


def get_file_version_suffix_if_exists(current_file: Dict, check_in_display: bool = False) -> Optional[str]:
    """
    Checks if current YML file name is versioned or no, e.g, ends with v<number>.
    Args:
        current_file (Dict): Dict representing YML data of an integration or script.
        check_in_display (bool): Whether to get name by 'display' field or not (by 'name' field).

    Returns:
        (Optional[str]): Number of the version as a string, if the file ends with version suffix. None otherwise.
    """
    versioned_file_regex = r'v([0-9]+)$'
    name = current_file.get('display') if check_in_display else current_file.get('name')
    if not name:
        return None
    matching_regex = re.findall(versioned_file_regex, name.lower())
    if matching_regex:
        return matching_regex[-1]
    return None


def get_all_incident_and_indicator_fields_from_id_set(id_set_file, entity_type):
    fields_list = []
    for item in ['IncidentFields', 'IndicatorFields']:
        all_item_fields = id_set_file.get(item)
        for item_field in all_item_fields:
            for field, field_info in item_field.items():
                if entity_type == 'mapper' or entity_type == 'old classifier':
                    fields_list.append(field_info.get('name', ''))
                    fields_list.append(field.replace('incident_', '').replace('indicator_', ''))
                elif entity_type == 'layout':
                    fields_list.append(field.replace('incident_', '').replace('indicator_', ''))
    return fields_list


def item_type_to_content_items_header(item_type):
    converter = {
        "incidenttype": "incidentType",
        "reputation": "indicatorType",
        "indicatorfield": "indicatorField",
        "incidentfield": "incidentField",
        "layoutscontainer": "layout",
        "betaintegration": "integration",

        # GOM
        "genericdefinition": "genericDefinition",
        "genericfield": "genericField",
        "genericmodule": "genericModule",
        "generictype": "genericType",

        # SIEM content
        "correlationrule": "correlationRule",
        "modelingrule": "modelingRule",
        "parsingrule": "parsingRule",
        "xdrctemplate": "XDRCTemplate"
    }

    return f'{converter.get(item_type, item_type)}s'


def is_object_in_id_set(object_id, item_type, pack_info_from_id_set):
    """
        Check if the given object is part of the packs items that are present in the Packs section in the id set.
        This is assuming that the id set is based on the version that has, under each pack, the items it contains.

    Args:
        object_name: name of object of interest.
        object_type: type of object of interest.
        packs_section_from_id_set: the pack object under the key Packs in the previously given id set.

    Returns:

    """
    content_items = pack_info_from_id_set.get('ContentItems', {})
    items_ids = content_items.get(item_type_to_content_items_header(item_type), [])

    return object_id in items_ids


def is_string_uuid(string_to_check: str):
    """
    Check if a given string is from uuid type
    Args:
        string_to_check: string

    Returns:
        bool. True if the string match uuid type, else False

    """
    return bool(re.fullmatch(UUID_REGEX, string_to_check))


def extract_multiple_keys_from_dict(key: str, var: dict):
    """
    Args:
        key: string representing a re-occurring field in dictionary
        var: nested dictionary (can contain both nested lists and nested dictionary)

    Returns: A generator that generates value in an occurrence of the nested key in var.
    """
    if hasattr(var, 'items'):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in extract_multiple_keys_from_dict(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in extract_multiple_keys_from_dict(key, d):
                        yield result


def find_file(root_path, file_name):
    """Find a file with a given file name under a given root path.
    Returns:
        str: The full file path from root path if exists, else return empty string.
    """
    for file in os.listdir(root_path):
        file_path = os.path.join(root_path, file)
        if file_path.endswith(file_name):
            return file_path
        elif os.path.isdir(file_path):
            found_file = find_file(file_path, file_name)
            if found_file:
                return found_file
    return ''


@lru_cache()
def get_file_displayed_name(file_path):
    """Gets the file name that is displayed in the UI by the file's path.
    If there is no displayed name - returns the file name"""
    file_type = find_type(file_path)
    if FileType.INTEGRATION == file_type:
        return get_yaml(file_path).get('display')
    elif file_type in [FileType.SCRIPT, FileType.TEST_SCRIPT, FileType.PLAYBOOK, FileType.TEST_PLAYBOOK]:
        return get_yaml(file_path).get('name')
    elif file_type in [FileType.MAPPER, FileType.CLASSIFIER, FileType.INCIDENT_FIELD, FileType.INCIDENT_TYPE,
                       FileType.INDICATOR_FIELD, FileType.LAYOUTS_CONTAINER, FileType.PRE_PROCESS_RULES,
                       FileType.DASHBOARD, FileType.WIDGET,
                       FileType.REPORT, FileType.JOB, FileType.WIZARD]:
        res = get_json(file_path)
        return res.get('name') if isinstance(res, dict) else res[0].get('name')
    elif file_type == FileType.OLD_CLASSIFIER:
        return get_json(file_path).get('brandName')
    elif file_type == FileType.LAYOUT:
        return get_json(file_path).get('TypeName')
    elif file_type == FileType.REPUTATION:
        return get_json(file_path).get('id')
    else:
        return os.path.basename(file_path)


def compare_context_path_in_yml_and_readme(yml_dict, readme_content):
    """
    Gets both README and YML file of Integration and compares the context path between them.
    Scripts are not being checked.
    Args:
        yml_dict: a dictionary representing YML content.
        readme_content: the content string of the readme file.
    Returns: A dictionary as following: {<command_name>:{'only in yml': <set of context paths found only in yml>,
                                                        'only in readme': <set of context paths found only in readme>}}
    """
    different_contexts: dict = {}

    # Gets the data from the README
    # the pattern to get the context part out of command section:
    context_section_pattern = r"\| *\*\*Path\*\* *\| *\*\*Type\*\* *\| *\*\*Description\*\* *\|.(.*?)#{3,5}"
    # the pattern to get the value in the first column under the outputs table:
    context_path_pattern = r"\| *(\S.*?\S) *\| *[^\|]* *\| *[^\|]* *\|"
    readme_content += "### "  # mark end of file so last pattern of regex will be recognized.
    commands = yml_dict.get("script", {})

    # handles scripts
    if not commands:
        return different_contexts
    commands = commands.get('commands', [])
    for command in commands:
        command_name = command.get('name')

        # Gets all context path in the relevant command section from README file
        command_section_pattern = fr" Base Command..`{command_name}`.(.*?)\n### "  # pattern to get command section
        command_section = re.findall(command_section_pattern, readme_content, re.DOTALL)
        if not command_section:
            continue
        if not command_section[0].endswith('###'):
            command_section[0] += '###'  # mark end of file so last pattern of regex will be recognized.
        context_section = re.findall(context_section_pattern, command_section[0], re.DOTALL)
        if not context_section:
            context_path_in_command = set()
        else:
            context_path_in_command = set(re.findall(context_path_pattern, context_section[0], re.DOTALL))

            # remove the header line ---- (could be of any length)
            for path in context_path_in_command:
                if not path.replace('-', ''):
                    context_path_in_command.remove(path)
                    break

        # handles cases of old integrations with context in 'important' section
        if 'important' in command:
            command.pop('important')

        # Gets all context path in the relevant command section from YML file
        existing_context_in_yml = set(extract_multiple_keys_from_dict("contextPath", command))

        # finds diff between YML and README
        only_in_yml_paths = existing_context_in_yml - context_path_in_command
        only_in_readme_paths = context_path_in_command - existing_context_in_yml
        if only_in_yml_paths or only_in_readme_paths:
            different_contexts[command_name] = {"only in yml": only_in_yml_paths,
                                                "only in readme": only_in_readme_paths}

    return different_contexts


def write_yml(yml_path: str, yml_data: Dict):
    with open(yml_path, 'w') as f:
        yaml.dump(yml_data, f)  # ruamel preservers multilines


def to_kebab_case(s: str):
    """
    Scan File => scan-file
    Scan File- => scan-file
    *scan,file => scan-file
    Scan     File => scan-file

    """
    if s:
        new_s = s.lower()
        new_s = re.sub('[ ,.-]+', '-', new_s)
        new_s = re.sub('[^A-Za-z0-9-]+', '', new_s)
        m = re.search('[a-z0-9]+(-[a-z]+)*', new_s)
        if m:
            return m.group(0)
        else:
            return new_s

    return s


def to_pascal_case(s: str):
    """
    Scan File => ScanFile
    Scan File- => ScanFile
    *scan,file => ScanFile
    Scan     File => ScanFile
    scan-file => ScanFile
    scan.file => ScanFile

    """
    if s:
        if re.search(r'^[A-Z][a-z]+(?:[A-Z][a-z]+)*$', s):
            return s

        new_s = s.lower()
        new_s = re.sub(r'[ -\.]+', '-', new_s)
        new_s = ''.join([t.title() for t in new_s.split('-')])
        new_s = re.sub(r'[^A-Za-z0-9]+', '', new_s)

        return new_s

    return s


def get_approved_usecases() -> list:
    """Gets approved list of usecases from content master

    Returns:
        List of approved usecases
    """
    return get_remote_file(
        'Tests/Marketplace/approved_usecases.json',
        git_content_config=GitContentConfig(repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME)
    ).get('approved_list', [])


def get_approved_tags() -> list:
    """Gets approved list of tags from content master

    Returns:
        List of approved tags
    """
    return get_remote_file(
        'Tests/Marketplace/approved_tags.json',
        git_content_config=GitContentConfig(repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME)
    ).get('approved_list', [])


def get_pack_metadata(file_path: str) -> dict:
    """ Get the pack_metadata dict, of the pack containing the given file path.

    Args:
        file_path(str): file path

    Returns: pack_metadata of the pack, that source_file related to,
        on failure returns {}

    """
    pack_path = file_path if PACKS_DIR in file_path else os.path.realpath(__file__)
    match = re.search(rf".*{PACKS_DIR}[/\\]([^/\\]+)[/\\]?", pack_path)
    directory = match.group() if match else ''

    try:
        metadata_path = os.path.join(directory, PACKS_PACK_META_FILE_NAME)
        pack_metadata, _ = get_dict_from_file(metadata_path)
        return pack_metadata
    except Exception:
        return {}


def is_pack_path(input_path: str) -> bool:
    """
    Checks whether pack given in input path is for a pack.
    Args:
        input_path (str): Input path.
    Examples
        - input_path = 'Packs/BitcoinAbuse
          Returns: True
        - input_path = 'Packs/BitcoinAbuse/Layouts'
          Returns: False
    Returns:
        (bool):
        - True if the input path is for a given pack.
        - False if the input path is not for a given pack.
    """
    return os.path.basename(os.path.dirname(input_path)) == PACKS_DIR


def get_relative_path_from_packs_dir(file_path: str) -> str:
    """Get the relative path for a given file_path starting in the Packs directory"""
    if PACKS_DIR not in file_path or file_path.startswith(PACKS_DIR):
        return file_path

    return file_path[file_path.find(PACKS_DIR):]


def is_uuid(s: str) -> Optional[Match]:
    """Checks whether given string is a UUID

    Args:
         s (str): The string to check if it is a UUID

    Returns:
        Match: Returns the match if given string is a UUID, otherwise None
    """
    return re.match(UUID_REGEX, s)


def get_release_note_entries(version='') -> list:
    """
    Gets the release notes entries for the current version.

    Args:
        version: The current demisto-sdk version.

    Return:
        list: A list of the release notes given from the CHANGELOG file.
    """

    changelog_file_content = get_remote_file(full_file_path='CHANGELOG.md',
                                             return_content=True,
                                             git_content_config=GitContentConfig(repo_name='demisto/demisto-sdk')
                                             ).decode('utf-8').split('\n')

    if not version or 'dev' in version:
        version = 'Changelog'

    if f'# {version}' not in changelog_file_content:
        return []

    result = changelog_file_content[changelog_file_content.index(f'# {version}') + 1:]
    result = result[:result.index('')]

    return result


def get_current_usecases() -> list:
    """Gets approved list of usecases from current branch (only in content repo).

    Returns:
        List of approved usecases from current branch
    """
    if not is_external_repository():
        approved_usecases_json, _ = get_dict_from_file('Tests/Marketplace/approved_usecases.json')
        return approved_usecases_json.get('approved_list', [])
    return []


def get_current_tags() -> list:
    """Gets approved list of tags from current branch (only in content repo).

    Returns:
        List of approved tags from current branch
    """
    if not is_external_repository():
        approved_tags_json, _ = get_dict_from_file('Tests/Marketplace/approved_tags.json')
        return approved_tags_json.get('approved_list', [])
    return []


@contextmanager
def suppress_stdout():
    """
        Temporarily suppress console output without effecting error outputs.
        Example of use:

            with suppress_stdout():
                print('This message will not be printed')
            print('This message will be printed')
    """
    with open(os.devnull, "w") as devnull:
        try:
            old_stdout = sys.stdout
            sys.stdout = devnull
            yield
        finally:
            sys.stdout = old_stdout


def get_definition_name(path: str, pack_path: str) -> Optional[str]:
    r"""
        param:
            path (str): path to the file which needs a definition name (generic field\generic type file)
            pack_path (str): relevant pack path

        :rtype: ``str``
        :return:
            for generic type and generic field return associated generic definition name folder

    """

    try:
        file_dictionary = get_json(path)
        definition_id = file_dictionary['definitionId']
        generic_def_path = os.path.join(pack_path, 'GenericDefinitions')
        file_names_lst = os.listdir(generic_def_path)
        for file in file_names_lst:
            if str.find(file, definition_id):
                def_file_path = os.path.join(generic_def_path, file)
                def_file_dictionary = get_json(def_file_path)
                cur_id = def_file_dictionary["id"]
                if cur_id == definition_id:
                    return def_file_dictionary["name"]

        print("Was unable to find the file for definitionId " + definition_id)
        return None

    except FileNotFoundError or AttributeError:
        print("Error while retrieving definition name for definitionId " + definition_id +
              "\n Check file structure and make sure all relevant fields are entered properly")
        return None


def is_iron_bank_pack(file_path):
    metadata = get_pack_metadata(file_path)
    return PACK_METADATA_IRON_BANK_TAG in metadata.get('tags', [])


def get_script_or_sub_playbook_tasks_from_playbook(searched_entity_name: str, main_playbook_data: Dict) -> List[Dict]:
    """Get the tasks data for a task running the searched_entity_name (script/playbook).

    Returns:
        List. A list of dicts representing tasks running the searched_entity_name.
    """
    searched_tasks: List = []
    tasks = main_playbook_data.get('tasks', {})
    if not tasks:
        return searched_tasks

    for task_data in tasks.values():
        task_details = task_data.get('task', {})
        found_entity = searched_entity_name in {task_details.get('scriptName'), task_details.get('playbookName')}

        if found_entity:
            searched_tasks.append(task_data)

    return searched_tasks


def extract_docker_image_from_text(text):
    """
    Strips the docker image version from a given text.
    Args:
        text : the text to extract the docker image from
    Return:
        str. The docker image version if exists, otherwise, return None.
    """
    match = (re.search(r'(demisto/.+:([0-9]+)(((\.)[0-9]+)+))', text))
    if match:
        return match.group(1)
    else:
        return None


def get_current_repo() -> Tuple[str, str, str]:
    try:
        git_repo = git.Repo(os.getcwd(), search_parent_directories=True)
        parsed_git = giturlparse.parse(git_repo.remotes.origin.url)
        host = parsed_git.host
        if '@' in host:
            host = host.split('@')[1]
        return host, parsed_git.owner, parsed_git.repo
    except git.InvalidGitRepositoryError:
        print_warning('git repo is not found')
        return "Unknown source", '', ''


def get_item_marketplaces(item_path: str, item_data: Dict = None, packs: Dict[str, Dict] = None, item_type: str = None) -> List:
    """
    Return the supporting marketplaces of the item.

    Args:
        item_path: the item path.
        item_data: the item data.
        packs: the pack mapping from the ID set.
        item_type: The item type.

    Returns: the list of supporting marketplaces.
    """

    if item_type and item_type in SIEM_ONLY_ENTITIES:
        return [MarketplaceVersions.MarketplaceV2.value]

    if not item_data:
        file_type = Path(item_path).suffix
        item_data = get_file(item_path, file_type)

    # first check, check field 'marketplaces' in the item's file
    marketplaces = item_data.get('marketplaces', [])  # type: ignore

    # second check, check the metadata of the pack
    if not marketplaces:
        if 'pack_metadata' in item_path:
            # default supporting marketplace
            marketplaces = [MarketplaceVersions.XSOAR.value]
        else:
            pack_name = get_pack_name(item_path)
            if packs and packs.get(pack_name):
                marketplaces = packs.get(pack_name, {}).get('marketplaces', [MarketplaceVersions.XSOAR.value])
            else:
                marketplaces = get_mp_types_from_metadata_by_item(item_path)

    return marketplaces


def get_mp_types_from_metadata_by_item(file_path):
    """
    Get the supporting marketplaces for the given content item, defined by the mp field in the metadata.
    If the field doesnt exist in the pack's metadata, consider as xsoar only.
    Args:
        file_path: path to content item in content repo

    Returns:
        list of names of supporting marketplaces (current options are marketplacev2 and xsoar)
    """
    if METADATA_FILE_NAME in Path(file_path).parts:  # for when the type is pack, the item we get is the metadata path
        metadata_path = file_path
    else:
        metadata_path_parts = get_pack_dir(file_path)
        metadata_path = Path(*metadata_path_parts) / METADATA_FILE_NAME

    try:
        with open(metadata_path, 'r') as metadata_file:
            metadata = json.load(metadata_file)
            marketplaces = metadata.get(MARKETPLACE_KEY_PACK_METADATA)
            if not marketplaces:
                return [MarketplaceVersions.XSOAR.value]
            return marketplaces
    except FileNotFoundError:
        return []


def get_pack_dir(path):
    """
    Used for testing packs where the location of the "Packs" dir is not constant.
    Args:
        path: path of current file

    Returns:
        the path starting from Packs dir

    """
    parts = Path(path).parts
    for index in range(len(parts)):
        if parts[index] == 'Packs':
            return parts[:index + 2]
    return []


@contextmanager
def ProcessPoolHandler() -> ProcessPool:
    """ Process pool Handler which terminate all processes in case of Exception.

    Yields:
        ProcessPool: Pebble process pool.
    """
    with ProcessPool(max_workers=3) as pool:
        try:
            yield pool
        except Exception:
            print_error("Gracefully release all resources due to Error...")
            raise
        finally:
            pool.close()
            pool.join()


def wait_futures_complete(futures: List[ProcessFuture], done_fn: Callable):
    """Wait for all futures to complete, Raise exception if occurred.

    Args:
        futures: futures to wait for.
        done_fn: Function to run on result.
    Raises:
        Exception: Raise caught exception for further cleanups.
    """
    for future in as_completed(futures):
        try:
            result = future.result()
            done_fn(result)
        except Exception as e:
            print_error(e)
            raise


def get_api_module_dependencies(pkgs, id_set_path, verbose):
    """
    Get all paths to integrations and scripts dependent on api modules that are found in the modified files.
    Args:
        pkgs: the pkgs paths found as modified to run lint on (including the api module files)
        id_set_path: path to id set
        verbose: print found dependencies or not
    Returns:
        a list of the paths to the scripts and integration found dependent on the modified api modules.
    """

    id_set = open_id_set_file(id_set_path)
    changed_api_modules = {pkg.name for pkg in pkgs if API_MODULES_PACK in pkg.parts}
    scripts = id_set.get(IdSetKeys.SCRIPTS.value, [])
    integrations = id_set.get(IdSetKeys.INTEGRATIONS.value, [])
    using_scripts, using_integrations = [], []
    for script in scripts:
        script_info = list(script.values())[0]
        script_name = script_info.get('name')
        script_api_modules = script_info.get('api_modules', [])
        if intersection := changed_api_modules & set(script_api_modules):
            if verbose:
                print(f"found script {script_name} dependent on {intersection}")
            using_scripts.extend(list(script.values()))

    for integration in integrations:
        integration_info = list(integration.values())[0]
        integration_name = integration_info.get('name')
        script_api_modules = integration_info.get('api_modules', [])
        if intersection := changed_api_modules & set(script_api_modules):
            if verbose:
                print(f"found integration {integration_name} dependent on {intersection}")
            using_integrations.extend(list(integration.values()))

    using_scripts_pkg_paths = [Path(script.get('file_path')).parent.absolute() for
                               script in using_scripts]
    using_integrations_pkg_paths = [Path(integration.get('file_path')).parent.absolute() for
                                    integration in using_integrations]
    return list(set(using_integrations_pkg_paths + using_scripts_pkg_paths))


def listdir_fullpath(dir_name: str) -> List[str]:
    return [os.path.join(dir_name, f) for f in os.listdir(dir_name)]


def get_scripts_and_commands_from_yml_data(data, file_type):
    """Get the used scripts, playbooks and commands from the yml data

    Args:
        data: The yml data as extracted with get_yaml
        file_type: The FileType of the data provided.

    Return (list of found { 'id': command name, 'source': command source }, list of found script and playbook names)
    """
    commands = []
    detailed_commands = []
    scripts_and_pbs = []
    if file_type in {FileType.TEST_PLAYBOOK, FileType.PLAYBOOK}:
        tasks = data.get('tasks')
        for task_num in tasks.keys():
            task = tasks[task_num]
            inner_task = task.get('task')
            task_type = task.get('type')
            if inner_task and task_type == 'regular' or task_type == 'playbook':
                if inner_task.get('iscommand'):
                    commands.append(inner_task.get('script'))
                else:
                    if task_type == 'playbook':
                        scripts_and_pbs.append(inner_task.get('playbookName'))
                    elif inner_task.get('scriptName'):
                        scripts_and_pbs.append(inner_task.get('scriptName'))
        if file_type == FileType.PLAYBOOK:
            playbook_id = get_entity_id_by_entity_type(data, PLAYBOOKS_DIR)
            scripts_and_pbs.append(playbook_id)

    if file_type == FileType.SCRIPT:
        script_id = get_entity_id_by_entity_type(data, SCRIPTS_DIR)
        scripts_and_pbs = [script_id]
        if data.get('dependson'):
            commands = data.get('dependson').get('must', [])

    if file_type == FileType.INTEGRATION:
        integration_commands = data.get('script', {}).get('commands')
        for integration_command in integration_commands:
            commands.append(integration_command.get('name'))

    for command in commands:
        command_parts = command.split('|||')
        if len(command_parts) == 2:
            detailed_commands.append({
                'id': command_parts[1],
                'source': command_parts[0]
            })
        else:
            detailed_commands.append({
                'id': command_parts[0]
            })

    return detailed_commands, scripts_and_pbs


def alternate_item_fields(content_item):
    """
    Go over all of the given content item fields and if there is a field with an alternative name, which is marked
    by '_x2', use that value as the value of the original field (the corresponding one without the '_x2' suffix).
    Args:
        content_item: content item object

    """
    current_dict = content_item.to_dict() if not isinstance(content_item, dict) else content_item
    copy_dict = current_dict.copy()  # for modifying dict while iterating
    for field, value in copy_dict.items():
        if field.endswith('_x2'):
            current_dict[field[:-3]] = value
            current_dict.pop(field)
        elif isinstance(current_dict[field], dict):
            alternate_item_fields(current_dict[field])
        elif isinstance(current_dict[field], list):
            for item in current_dict[field]:
                if isinstance(item, dict):
                    alternate_item_fields(item)


def should_alternate_field_by_item(content_item, id_set):
    """
    Go over the given content item and check if it should be modified to use its alternative fields, which is determined
    by the field 'has_alternative_meta' in the id set.
    Args:
        content_item: content item object
        id_set: parsed id set dict

    Returns: True if should alterante fields, false otherwise

    """
    commonfields = content_item.get('commonfields')
    item_id = commonfields.get('id') if commonfields else content_item.get('id')

    item_type = content_item.type()
    id_set_item_type = id_set.get(FileTypeToIDSetKeys.get(item_type))
    for item in id_set_item_type:
        if list(item.keys())[0] == item_id:
            return item.get(item_id, {}).get('has_alternative_meta', False)
    return False


def get_url_with_retries(url: str, retries: int, backoff_factor: int = 1, **kwargs):
    kwargs['stream'] = True
    session = requests.Session()
    exception = Exception()
    for _ in range(retries):
        response = session.get(url, **kwargs)
        try:
            response.raise_for_status()
        except HTTPError as error:
            exception = error
        else:
            return response
        sleep(backoff_factor)
    raise exception


def order_dict(data):
    """
    Order dict by default order
    """
    return OrderedDict({k: order_dict(v) if isinstance(v, dict) else v
                        for k, v in sorted(data.items())})


def extract_none_deprecated_command_names_from_yml(yml_data: dict) -> list:
    """
    Go over all the commands in a yml file and return their names.
    Args:
        yml_data (dict): the yml content as a dict

    Returns:
        list: a list of all the commands names
    """
    commands_ls = []
    for command in yml_data.get('script', {}).get('commands', {}):
        if command.get('name') and not command.get('deprecated'):
            commands_ls.append(command.get('name'))
    return commands_ls


def extract_deprecated_command_names_from_yml(yml_data: dict) -> list:
    """
    Go over all the commands in a yml file and return their names.
    Args:
        yml_data (dict): the yml content as a dict

    Returns:
        list: a list of all the commands names
    """
    commands_ls = []
    for command in yml_data.get('script', {}).get('commands', {}):
        if command.get('deprecated'):
            commands_ls.append(command.get('name'))
    return commands_ls


def remove_copy_and_dev_suffixes_from_str(field_name: str) -> str:
    for _ in range(field_name.count('_')):
        for suffix in SUFFIX_TO_REMOVE:
            if field_name.endswith(suffix):
                field_name = field_name[:-len(suffix)]
    return field_name


def get_display_name(file_path, file_data={}) -> str:
    """ Gets the entity display name from the file.

        :param file_path: The entity file path
        :param file_data: The entity file data

        :rtype: ``str``
        :return The display name
    """
    if not file_data:
        file_extension = os.path.splitext(file_path)[1]
        if file_extension in ['.yml', '.json']:
            file_data = get_file(file_path, file_extension)

    if 'display' in file_data:
        name = file_data.get('display', None)
    elif 'layout' in file_data and isinstance(file_data['layout'], dict):
        name = file_data['layout'].get('id')
    elif 'name' in file_data:
        name = file_data.get('name', None)
    elif 'TypeName' in file_data:
        name = file_data.get('TypeName', None)
    elif 'brandName' in file_data:
        name = file_data.get('brandName', None)
    elif 'id' in file_data:
        name = file_data.get('id', None)
    elif 'trigger_name' in file_data:
        name = file_data.get('trigger_name')

    elif 'dashboards_data' in file_data and file_data.get('dashboards_data') \
            and isinstance(file_data['dashboards_data'], list):
        dashboard_data = file_data.get('dashboards_data', [{}])[0]
        name = dashboard_data.get('name')

    elif 'templates_data' in file_data and file_data.get('templates_data') \
            and isinstance(file_data['templates_data'], list):
        r_name = file_data.get('templates_data', [{}])[0]
        name = r_name.get('report_name')

    else:
        name = os.path.basename(file_path)
    return name


def get_invalid_incident_fields_from_mapper(
    mapper_incident_fields: Dict[str, Dict], mapping_type: str, content_fields: List
) -> List[str]:
    """
    Get a list of incident fields which are not part of the content items (not part of id_json) from a specific
    interalMapping attribute.

    Args:
        mapper_incident_fields (dict[str, dict]): a dict of incident fields which belongs to a specific interalMapping.
        mapping_type (str): type of the mapper, either 'mapping-incoming' or 'mapping-outgoing'.
        content_fields (list[str]): list of available content fields.

    Returns:
        list[str]: all the invalid incident fields which are not part of the content items.

    Raises:
        ValueError: in case the mapping type has an incorrect value provided.
    """
    if mapping_type not in {'mapping-incoming', 'mapping-outgoing'}:
        raise ValueError(f'Invalid mapping-type value {mapping_type}, should be: mapping-incoming/mapping-outgoing')

    non_existent_fields = []

    for inc_name, inc_info in mapper_incident_fields.items():
        # incoming mapper
        if mapping_type == "mapping-incoming":
            if inc_name not in content_fields and inc_name.lower() not in content_fields:
                non_existent_fields.append(inc_name)
        # outgoing mapper
        if mapping_type == "mapping-outgoing":
            # for inc timer type: "field.StartDate, and for using filters: "simple": "".
            if simple := inc_info.get('simple'):
                if '.' in simple:
                    simple = simple.split('.')[0]
                if simple not in content_fields and simple.lower() not in content_fields:
                    non_existent_fields.append(inc_name)

    return non_existent_fields


def get_invalid_incident_fields_from_layout(layout_incident_fields: List[Dict], content_fields: List[str]) -> List[str]:
    """
    Get a list of incident fields which are not part of the content items (not part of id_json) from a specific
    layout item/section.

    Args:
        layout_incident_fields (list[dict]): a list of incident fields which
            belongs to a specific section/item in the layout.
        content_fields (list[str]): list of available content fields.

    Returns:
        list[str]: all the invalid incident fields which are not part of the content items.
    """
    non_existent_fields = []

    if layout_incident_fields and content_fields:
        for incident_field_info in layout_incident_fields:
            inc_field_id = normalize_field_name(field=incident_field_info.get('fieldId', ''))
            if inc_field_id and inc_field_id.lower() not in content_fields and inc_field_id not in content_fields:
                non_existent_fields.append(inc_field_id)

    return non_existent_fields


def normalize_field_name(field: str) -> str:
    """
    Get the raw field from a layout/mapper field.

    Input Example:
        field = incident_employeenumber

    Args:
        field (str): the incident/indicator field.
    """
    return field.replace('incident_', '').replace('indicator_', '')


def string_to_bool(
        input_: str,
        accept_lower_case: bool = True,
        accept_title: bool = True,
        accept_upper_case: bool = False,
        accept_yes_no: bool = False,
        accept_int: bool = False,
        accept_single_letter: bool = False,
) -> Optional[bool]:
    if not isinstance(input_, str):
        raise ValueError('cannot convert non-string to bool')

    _considered_true = ['true']
    _considered_false = ['false']

    for (condition, true_value, false_value) in (
            (accept_yes_no, 'yes', 'no'),
            (accept_int, '1', '0')
    ):
        if condition:
            _considered_true.append(true_value)
            _considered_false.append(false_value)

    considered_true: Set[str] = set()
    considered_false: Set[str] = set()

    for (condition, func) in (
            (accept_lower_case, lambda x: x.lower()),
            (accept_title, lambda x: x.title()),
            (accept_upper_case, lambda x: x.upper()),
    ):
        if condition:
            considered_true.update(map(func, _considered_true))
            considered_false.update(map(func, _considered_false))

    if accept_single_letter:
        considered_true.update(tuple(_[0] for _ in considered_true))  # note this takes considered_true as input
        considered_false.update(tuple(_[0] for _ in considered_false))

    if input_ in considered_true:
        return True

    if input_ in considered_false:
        return False

    raise ValueError(f'cannot convert string {input_} to bool')


def field_to_cli_name(field_name: str) -> str:
    """
    Returns the CLI name of an incident/indicator field by removing non letters/numbers
    characters and lowering capitalized letters.

    Input Example:
        field = Employee Number
    Output:
        employeenumber

    Args:
        field_name (str): the incident/indicator field name.
    """
    return re.sub(NON_LETTERS_OR_NUMBERS_PATTERN, '', field_name).lower()

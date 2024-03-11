from __future__ import annotations

import contextlib
import glob
import os
import re
import shlex
import sys
import time
import traceback
import urllib.parse
import xml.etree.ElementTree as ET
from abc import ABC
from collections import OrderedDict
from concurrent.futures import as_completed
from configparser import ConfigParser, MissingSectionHeaderError
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from functools import lru_cache, wraps
from hashlib import sha1
from io import StringIO, TextIOWrapper
from pathlib import Path, PosixPath
from subprocess import PIPE, Popen
from time import sleep
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Match,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)

import demisto_client
import git
import giturlparse
import google
import requests
import urllib3
from bs4.dammit import UnicodeDammit
from google.cloud import secretmanager
from packaging.version import Version
from pebble import ProcessFuture, ProcessPool
from requests.exceptions import HTTPError

from demisto_sdk.commands.common.constants import (
    ALL_FILES_VALIDATION_IGNORE_WHITELIST,
    API_MODULES_PACK,
    ASSETS_MODELING_RULES_DIR,
    CLASSIFIERS_DIR,
    CONF_JSON_FILE_NAME,
    CONTENT_ENTITIES_DIRS,
    CORRELATION_RULES_DIR,
    DASHBOARDS_DIR,
    DEF_DOCKER,
    DEF_DOCKER_PWSH,
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
    DEMISTO_GIT_PRIMARY_BRANCH,
    DEMISTO_GIT_UPSTREAM,
    DOC_FILES_DIR,
    ENV_DEMISTO_SDK_MARKETPLACE,
    ENV_SDK_WORKING_OFFLINE,
    GENERIC_FIELDS_DIR,
    GENERIC_TYPES_DIR,
    ID_IN_COMMONFIELDS,
    ID_IN_ROOT,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INTEGRATIONS_DIR,
    ISO_TIMESTAMP_FORMAT,
    JOBS_DIR,
    LAYOUT_RULES_DIR,
    LAYOUTS_DIR,
    LISTS_DIR,
    MARKETPLACE_KEY_PACK_METADATA,
    MARKETPLACE_TO_CORE_PACKS_FILE,
    MODELING_RULES_DIR,
    NON_LETTERS_OR_NUMBERS_PATTERN,
    OFFICIAL_CONTENT_GRAPH_PATH,
    OFFICIAL_CONTENT_ID_SET_PATH,
    OFFICIAL_INDEX_JSON_PATH,
    PACK_METADATA_IRON_BANK_TAG,
    PACK_METADATA_SUPPORT,
    PACKAGE_SUPPORTING_DIRECTORIES,
    PACKAGE_YML_FILE_REGEX,
    PACKS_DIR,
    PACKS_DIR_REGEX,
    PACKS_FOLDER,
    PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME,
    PARSING_RULES_DIR,
    PLAYBOOKS_DIR,
    PRE_PROCESS_RULES_DIR,
    RELEASE_NOTES_DIR,
    RELEASE_NOTES_REGEX,
    REPORTS_DIR,
    SCRIPTS_DIR,
    SIEM_ONLY_ENTITIES,
    STRING_TO_BOOL_MAP,
    TABLE_INCIDENT_TO_ALERT,
    TEST_PLAYBOOKS_DIR,
    TESTS_AND_DOC_DIRECTORIES,
    TRIGGER_DIR,
    TYPE_PWSH,
    UNRELEASE_HEADER,
    URL_REGEX,
    UUID_REGEX,
    WIDGETS_DIR,
    XDRC_TEMPLATE_DIR,
    XSIAM_DASHBOARDS_DIR,
    XSIAM_REPORTS_DIR,
    XSOAR_CONFIG_FILE,
    XSOAR_SUPPORT,
    FileType,
    IdSetKeys,
    MarketplaceVersions,
    PathLevel,
    urljoin,
)
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import (
    XSOAR_Handler,
    YAML_Handler,
)
from demisto_sdk.commands.common.logger import logger

if TYPE_CHECKING:
    from demisto_sdk.commands.content_graph.interface import ContentGraphInterface

yaml_safe_load = YAML_Handler(typ="safe")

urllib3.disable_warnings()

GRAPH_SUPPORTED_FILE_TYPES = ["yml", "json"]


class TagParser:
    def __init__(self, marketplace_tag):
        self.pattern = rf"<~{marketplace_tag}>.*?</~{marketplace_tag}>|<~{marketplace_tag}>\n.*?\n</~{marketplace_tag}>\n"
        self.only_tags_pattern = rf"<~{marketplace_tag}>|</~{marketplace_tag}>|<~{marketplace_tag}>\n|\n</~{marketplace_tag}>\n"

    def parse(self, text: str, remove_tag: Optional[bool] = False) -> str:
        """
        Given a prefix and suffix of an expected tag, remove the tag and the text it's wrapping, or just the wrappers
        Args:
            text (str): text that may contain given tags.
            remove_tag (bool): overrides remove_tag_text value. Determines whether to remove the tag

        Returns:
            Text with no wrapper tags.
        """
        if remove_tag:
            text = re.sub(self.pattern, "", text, flags=re.DOTALL)

        text = re.sub(self.only_tags_pattern, "", text, flags=re.DOTALL)
        return text


class MarketplaceTagParser:
    XSOAR_TAG = "XSOAR"
    XSIAM_TAG = "XSIAM"
    XPANSE_TAG = "XPANSE"
    XSOAR_SAAS_TAG = "XSOAR_SAAS"
    XSOAR_ON_PREM_TAG = "XSOAR_ON_PREM"

    def __init__(self, marketplace: str = MarketplaceVersions.XSOAR.value):
        self.marketplace = marketplace

        self._xsoar_parser = TagParser(marketplace_tag=self.XSOAR_TAG)
        self._xsiam_parser = TagParser(marketplace_tag=self.XSIAM_TAG)
        self._xpanse_parser = TagParser(marketplace_tag=self.XPANSE_TAG)
        self._xsoar_saas_parser = TagParser(marketplace_tag=self.XSOAR_SAAS_TAG)
        self._xsoar_on_prem_parser = TagParser(marketplace_tag=self.XSOAR_ON_PREM_TAG)

    @property
    def marketplace(self):
        return self._marketplace

    @marketplace.setter
    def marketplace(self, marketplace):
        self._marketplace = marketplace
        self._should_remove_xsoar_text = marketplace not in [
            MarketplaceVersions.XSOAR.value,
            MarketplaceVersions.XSOAR_ON_PREM.value,
            MarketplaceVersions.XSOAR_SAAS.value,
        ]
        self._should_remove_xsiam_text = (
            marketplace != MarketplaceVersions.MarketplaceV2.value
        )
        self._should_remove_xpanse_text = (
            marketplace != MarketplaceVersions.XPANSE.value
        )
        self._should_remove_xsoar_saas_text = (
            marketplace != MarketplaceVersions.XSOAR_SAAS.value
        )
        self._should_remove_xsoar_on_prem_text = marketplace not in [
            MarketplaceVersions.XSOAR_ON_PREM.value,
            MarketplaceVersions.XSOAR.value,
        ]

    def parse_text(self, text):
        # Remove the tags of the products if specified should_remove.
        text = self._xsoar_parser.parse(
            remove_tag=self._should_remove_xsoar_text, text=text
        )
        text = self._xsoar_saas_parser.parse(
            remove_tag=self._should_remove_xsoar_saas_text, text=text
        )
        text = self._xsiam_parser.parse(
            remove_tag=self._should_remove_xsiam_text, text=text
        )
        text = self._xsoar_on_prem_parser.parse(
            remove_tag=self._should_remove_xsoar_on_prem_text, text=text
        )
        return self._xpanse_parser.parse(
            remove_tag=self._should_remove_xpanse_text, text=text
        )


MARKETPLACE_TAG_PARSER = None

LAYOUT_CONTAINER_FIELDS = {
    "details",
    "detailsV2",
    "edit",
    "close",
    "mobile",
    "quickView",
    "indicatorsQuickView",
    "indicatorsDetails",
}
SDK_PYPI_VERSION = r"https://pypi.org/pypi/demisto-sdk/json"

SUFFIX_TO_REMOVE = ("_dev", "_copy")


class NoInternetConnectionException(Exception):
    """
    This exception is raised in methods that require an internet connection, when the SDK is defined as working offline.
    """

    pass


def generate_xsiam_normalized_name(file_name, prefix):
    if file_name.startswith(f"external-{prefix}-"):
        return file_name
    elif file_name.startswith(f"{prefix}-"):
        return file_name.replace(f"{prefix}-", f"external-{prefix}-")
    else:
        return f"external-{prefix}-{file_name}"


def get_mp_tag_parser():
    global MARKETPLACE_TAG_PARSER
    if MARKETPLACE_TAG_PARSER is None:
        MARKETPLACE_TAG_PARSER = MarketplaceTagParser(
            os.getenv(ENV_DEMISTO_SDK_MARKETPLACE, MarketplaceVersions.XSOAR.value)
        )
    return MARKETPLACE_TAG_PARSER


def get_yml_paths_in_dir(project_dir: str | Path) -> Tuple[list, str]:
    """
    Gets the project directory and returns the path of the first yml file in that directory
    :param project_dir: path to the project_dir
    :return: first returned argument is the list of all yml files paths in the directory, second returned argument is a
    string path to the first yml file in project_dir
    """
    project_dir_path = Path(project_dir)
    yml_files = [str(path) for path in project_dir_path.glob("*.yml")]

    if not yml_files:
        return [], ""

    return yml_files, yml_files[0]


def get_files_in_dir(
    project_dir: str,
    file_endings: list,
    recursive: bool = True,
    ignore_test_files: bool = False,
    exclude_list: Optional[list] = None,
) -> list:
    """
    Gets the project directory and returns the path of all yml, json and py files in it
    Args:
        project_dir: String path to the project_dir
        file_endings: List of file endings to search for in a given directory
        recursive: Indicates whether search should be recursive or not
        exclude_list: List of file/directory names to exclude.
    :return: The path of files with file_endings in the current dir
    """
    files = []
    excludes = []
    exclude_all_list = exclude_list.copy() if exclude_list else []
    if ignore_test_files:
        exclude_all_list.extend(TESTS_AND_DOC_DIRECTORIES)

    project_path = Path(project_dir)
    glob_function = project_path.rglob if recursive else project_path.glob
    for file_type in file_endings:
        pattern = f"*.{file_type}"
        if project_dir.endswith(file_type):
            return [project_dir]
        for exclude_item in exclude_all_list:
            exclude_pattern = f"**/{exclude_item}/" + pattern
            excludes.extend([str(f) for f in glob_function(exclude_pattern)])
        files.extend([str(f) for f in glob_function(pattern)])
    return list(set(files) - set(excludes))


def get_all_content_objects_paths_in_dir(project_dir_list: Optional[Iterable]):
    """
    Gets the project directory and returns the path of all yml, json and py files in it
    Args:
        project_dir_list: List or set with str paths
    :return: list of content files in the current dir with str relative paths
    """
    files: list = []
    if not project_dir_list:
        return files

    for file_path in project_dir_list:
        files.extend(
            get_files_in_dir(
                file_path, GRAPH_SUPPORTED_FILE_TYPES, ignore_test_files=True
            )
        )

    output = [get_relative_path_from_packs_dir(file) for file in files]

    return output


def src_root() -> Path:
    """Demisto-sdk absolute path from src root.

    Returns:
        Path: src root path.
    """
    git_dir = GitUtil().repo.working_tree_dir

    return Path(git_dir) / "demisto_sdk"  # type: ignore


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
        p = Popen(
            command.split(), stdout=PIPE, stderr=PIPE, universal_newlines=True, cwd=cwd
        )
    else:
        p = Popen(command.split(), cwd=cwd)  # type: ignore

    output, err = p.communicate()
    if err:
        if exit_on_error:
            logger.info(
                f"[red]Failed to run command {command}\nerror details:\n{err}[/red]"
            )
            sys.exit(1)
        else:
            raise RuntimeError(
                f"Failed to run command {command}\nerror details:\n{err}"
            )

    return output


def get_marketplace_to_core_packs() -> Dict[MarketplaceVersions, Set[str]]:
    """Getting the core pack from Github content

    Returns:
        A mapping from marketplace versions to their core packs.
    """
    if is_external_repository():
        return {}  # no core packs in external repos.

    mp_to_core_packs: Dict[MarketplaceVersions, Set[str]] = {}
    for mp in MarketplaceVersions:
        # for backwards compatibility mp_core_packs can be a list, but we expect a dict.
        try:
            mp_core_packs: Union[list, dict] = get_json(
                MARKETPLACE_TO_CORE_PACKS_FILE[mp],
            )
        except FileNotFoundError:
            mp_core_packs = get_remote_file(
                MARKETPLACE_TO_CORE_PACKS_FILE[mp],
                git_content_config=GitContentConfig(
                    repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME,
                    git_provider=GitProvider.GitHub,
                ),
            )
        if isinstance(mp_core_packs, list):
            mp_to_core_packs[mp] = set(mp_core_packs)
        else:
            mp_to_core_packs[mp] = set(mp_core_packs.get("core_packs_list", []))
    return mp_to_core_packs


def get_core_pack_list(marketplaces: List[MarketplaceVersions] = None) -> list:
    """Getting the core pack list from Github content

    Arguments:
        marketplaces: A list of the marketplaces to return core packs for.

    Returns:
        The core packs list.
    """
    result: Set[str] = set()
    if is_external_repository():
        return []  # no core packs in external repos.

    if marketplaces is None:
        marketplaces = list(MarketplaceVersions)

    try:
        for mp, core_packs in get_marketplace_to_core_packs().items():
            if mp in marketplaces:
                result.update(core_packs)
    except NoInternetConnectionException:
        logger.debug("SDK running in offline mode, returning core_packs=[]")
        return []
    return list(result)


def get_local_remote_file(
    full_file_path: str,
    tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
    return_content: bool = False,
):
    repo_git_util = GitUtil()
    git_path = repo_git_util.get_local_remote_file_path(full_file_path, tag)
    file_content = repo_git_util.get_local_remote_file_content(git_path)
    if return_content:
        if file_content:
            return file_content.encode()
        return file_content
    return get_file_details(file_content, full_file_path)


def get_remote_file_from_api(
    full_file_path: str,
    git_content_config: Optional[GitContentConfig],
    tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
    return_content: bool = False,
    encoding: Optional[str] = None,
) -> Union[bytes, Dict, List]:
    """
    Returns a remote file from Github/Gitlab repo using the api

    Args:
        full_file_path: file path in the GitHub/Gitlab repository
        git_content_config: GitContentConfig config object
        tag: from which commit / branch to take the file in the remote repository
        return_content: whether to return the raw content of the file (bytes)
        encoding: whether to decode the remote file with special encoding

    Returns:
        bytes | Dict | List: raw response of the file or as a python object (list, dict)
    """
    if not git_content_config:
        git_content_config = GitContentConfig()
    if git_content_config.git_provider == GitProvider.GitLab:
        full_file_path_quote_plus = urllib.parse.quote_plus(full_file_path)
        git_path = urljoin(
            git_content_config.base_api, "files", full_file_path_quote_plus, "raw"
        )
    else:  # github
        git_path = urljoin(git_content_config.base_api, tag, full_file_path)

    github_token: Optional[str] = None
    gitlab_token: Optional[str] = None
    try:
        github_token = git_content_config.CREDENTIALS.github_token
        gitlab_token = git_content_config.CREDENTIALS.gitlab_token
        if git_content_config.git_provider == GitProvider.GitLab:
            res = requests.get(
                git_path,
                params={"ref": tag},
                headers={"PRIVATE-TOKEN": gitlab_token},
                verify=False,
            )
            res.raise_for_status()
        else:  # Github
            res = requests.get(
                git_path,
                verify=False,
                timeout=10,
                headers={
                    "Authorization": f"Bearer {github_token}" if github_token else "",
                    "Accept": "application/vnd.github.VERSION.raw",
                },
            )  # Sometime we need headers
            if not res.ok:  # sometime we need param token
                res = requests.get(
                    git_path, verify=False, timeout=10, params={"token": github_token}
                )

        res.raise_for_status()
    except requests.exceptions.RequestException as exc:
        # Replace token secret if needed
        err_msg: str = (
            str(exc).replace(github_token, "XXX") if github_token else str(exc)
        )
        err_msg = err_msg.replace(gitlab_token, "XXX") if gitlab_token else err_msg
        if is_external_repository():
            logger.debug(
                f'[yellow]You are working in a private repository: "{git_content_config.current_repository}".\n'
                f"The github/gitlab token in your environment is undefined.\n"
                f"Getting file from local repository instead. \n"
                f"If you wish to get the file from the remote repository, \n"
                f"Please define your github or gitlab token in your environment.\n"
                f"`export {GitContentConfig.CREDENTIALS.ENV_GITHUB_TOKEN_NAME}=<TOKEN> or`\n"
                f"export {GitContentConfig.CREDENTIALS.ENV_GITLAB_TOKEN_NAME}=<TOKEN>[/yellow]"
            )
        logger.debug(
            f'[yellow]Could not find the old entity file under "{git_path}".\n'
            "please make sure that you did not break backward compatibility.\n"
            f"Reason: {err_msg}[/yellow]"
        )
        return {}

    file_content = res.content

    if return_content:
        return file_content
    if encoding:
        file_content = file_content.decode(encoding)  # type: ignore[assignment]

    return get_file_details(file_content, full_file_path)


def get_file_details(
    file_content,
    full_file_path: str,
) -> Dict:
    if full_file_path.endswith("json"):
        file_details = json.loads(file_content)
    elif full_file_path.endswith(("yml", "yaml")):
        file_details = yaml.load(file_content)
    elif full_file_path.endswith(".pack-ignore"):
        return file_content
    # if neither yml nor json then probably a CHANGELOG or README file.
    else:
        file_details = {}
    return file_details


@lru_cache(maxsize=128)
def get_remote_file(
    full_file_path: str,
    tag: str = DEMISTO_GIT_PRIMARY_BRANCH,
    return_content: bool = False,
    git_content_config: Optional[GitContentConfig] = None,
    default_value=None,
):
    """
    Args:
        full_file_path:The full path of the file.
        tag: The branch name. default is the content of DEMISTO_DEFAULT_BRANCH env variable.
        return_content: Determines whether to return the file's raw content or the dict representation of it.
        git_content_config: The content config to take the file from
        default_value: The method returns this value if using the SDK in offline mode. default_value cannot be None,
        as it will raise an exception.
    Returns:
        The file content in the required format.

    """
    if is_sdk_defined_working_offline():
        if default_value is None:
            raise NoInternetConnectionException
        return default_value
    if not tag:
        tag = DEMISTO_GIT_PRIMARY_BRANCH
    tag = tag.replace(f"{DEMISTO_GIT_UPSTREAM}/", "").replace("demisto/", "")
    if not git_content_config:
        try:
            if not (
                local_origin_content := get_local_remote_file(
                    full_file_path, tag, return_content
                )
            ):
                raise ValueError(
                    f"Got empty content from local-origin file {full_file_path}"
                )
            return local_origin_content
        except Exception as e:
            logger.debug(
                f"Could not get local remote file because of: {str(e)}\n"
                f"Searching the remote file content with the API.",
                exc_info=True,
            )
    return get_remote_file_from_api(
        full_file_path, git_content_config, tag, return_content
    )


def filter_files_on_pack(pack: str, file_paths_list="") -> set:
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


def filter_packagify_changes(
    modified_files, added_files, removed_files, tag=DEMISTO_GIT_PRIMARY_BRANCH
):
    """
    Mark scripts/integrations that were removed and added as modified.

    :param modified_files: list of modified files in branch
    :param added_files: list of new files in branch
    :param removed_files: list of removed files in branch
    :param tag: The branch name. default is the content of DEMISTO_DEFAULT_BRANCH env variable.

    :return: tuple of updated lists: (modified_files, updated_added_files, removed_files)
    """
    # map IDs to removed files
    packagify_diff: dict = {}
    for file_path in removed_files:
        if file_path.split("/")[0] in PACKAGE_SUPPORTING_DIRECTORIES:
            if PACKS_README_FILE_NAME in file_path:
                continue
            details = get_remote_file(file_path, tag)
            if details:
                uniq_identifier = "_".join(
                    [
                        details["name"],
                        details.get("fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION),
                        details.get("toversion", DEFAULT_CONTENT_ITEM_TO_VERSION),
                    ]
                )
                packagify_diff[uniq_identifier] = file_path

    updated_added_files = set()
    for file_path in added_files:
        if file_path.split("/")[0] in PACKAGE_SUPPORTING_DIRECTORIES:
            if PACKS_README_FILE_NAME in file_path:
                updated_added_files.add(file_path)
                continue
            details = get_file(file_path, raise_on_error=True)

            uniq_identifier = "_".join(
                [
                    details["name"],
                    details.get("fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION),
                    details.get("toversion", DEFAULT_CONTENT_ITEM_TO_VERSION),
                ]
            )
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


def get_child_directories(directory: str | Path) -> list[str]:
    """
    Get a list of all directories within a directory.
    Does not search recursively.
    Args:
        directory (str | Path): The directory to search in
    Returns:
        list[str]: A list of paths (in string format) of immediate child directories of the 'directory' argument
    """
    directory_path = Path(directory)

    if directory_path.is_dir():
        return [str(path) for path in directory_path.iterdir() if path.is_dir()]

    return []


def get_child_files(directory):
    """Return a list of paths of immediate child files of the 'directory' argument"""
    if not os.path.isdir(directory):
        return []
    child_files = [
        os.path.join(directory, path)
        for path in os.listdir(directory)
        if Path(directory, path).is_file()
    ]
    return child_files


@lru_cache
def git_remote_v():
    return run_command("git remote -v")


def has_remote_configured():
    """
    Checks to see if a remote named "upstream" is configured. This is important for forked
    repositories as it will allow validation against the demisto/content master branch as
    opposed to the master branch of the fork.
    :return: bool : True if remote is configured, False if not.
    """
    if re.search(GitContentConfig.CONTENT_GITHUB_UPSTREAM, git_remote_v()):
        return True
    else:
        return False


def is_origin_content_repo():
    """
    Checks to see if a remote named "origin" is configured. This check helps to determine if
    validation needs to be ran against the origin master branch or the upstream master branch
    :return: bool : True if remote is configured, False if not.
    """
    if re.search(GitContentConfig.CONTENT_GITHUB_ORIGIN, git_remote_v()):
        return True
    else:
        return False


@lru_cache
def get_last_remote_release_version():
    """
    Get latest release tag from PYPI.

    :return: tag
    """
    try:
        pypi_request = requests.get(SDK_PYPI_VERSION, verify=False, timeout=5)
        pypi_request.raise_for_status()
        pypi_json = pypi_request.json()
        version = pypi_json.get("info", {}).get("version", "")
        return version
    except Exception as exc:
        exc_msg = str(exc)
        if isinstance(exc, requests.exceptions.ConnectionError):
            exc_msg = (
                f'{exc_msg[exc_msg.find(">") + 3:-3]}.\n'
                f"This may happen if you are not connected to the internet."
            )
        logger.warning(
            f"Could not find the latest version of 'demisto-sdk'.\nError: {exc_msg}"
        )
        return ""


def safe_read_unicode(bytes_data: bytes) -> str:
    """
    Safely read unicode data from bytes.

    Args:
        bytes_data (bytes): bytes to read.

    Returns:
        str: A string representation of the parsed bytes.
    """
    try:
        return bytes_data.decode("utf-8")

    except UnicodeDecodeError:
        try:
            logger.debug(
                "Could not read data using UTF-8 encoding. Trying to auto-detect encoding..."
            )
            return UnicodeDammit(bytes_data).unicode_markup

        except UnicodeDecodeError:
            logger.error("Could not auto-detect encoding.")
            raise


def safe_write_unicode(
    write_method: Callable[[TextIOWrapper], Any],
    path: Path,
):
    # Write unicode content into a file.
    # If the destination file is not unicode, delete and re-write the content as unicode.

    def _write():
        with open(path, "w", encoding="utf-8") as f:
            write_method(f)

    try:
        _write()

    except UnicodeError:
        encoding = UnicodeDammit(path.read_bytes()).original_encoding
        if encoding == "utf-8":
            logger.error(
                f"{path} is encoded as unicode, cannot handle the error, raising it"
            )
            raise  # already a unicode file, the following code cannot fix it.

        logger.debug(
            f"deleting {path} - it will be rewritten as unicode (was {encoding})"
        )
        path.unlink()  # deletes the file
        logger.debug(f"rewriting {path} as")
        _write()  # recreates the file


@lru_cache
def get_file(
    file_path: str | Path,
    clear_cache: bool = False,
    return_content: bool = False,
    keep_order: bool = False,
    raise_on_error: bool = False,
    git_sha: Optional[str] = None,
):
    """
    Get file contents.
    if raise_on_error = False, this function will return empty dict
    """
    if clear_cache:
        get_file.cache_clear()
    file_path = Path(file_path)  # type: ignore[arg-type]
    if git_sha:
        if file_path.is_absolute():
            file_path = file_path.relative_to(get_content_path())
        return get_remote_file(
            str(file_path), tag=git_sha, return_content=return_content
        )

    type_of_file = file_path.suffix.lower()

    if not file_path.exists():
        file_path = Path(get_content_path()) / file_path  # type: ignore[arg-type]
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    try:
        file_content = safe_read_unicode(file_path.read_bytes())
        if return_content:
            return file_content
    except IOError as e:
        logger.error(f"Could not read file '{file_path}': {e}")
        logger.debug("Traceback:\n" + traceback.format_exc())
        return {}
    try:
        if type_of_file.lstrip(".") in {"yml", "yaml"}:
            replaced = StringIO(
                re.sub(r"(simple: \s*\n*)(=)(\s*\n)", r'\1"\2"\3', file_content)
            )
            return yaml.load(replaced) if keep_order else yaml_safe_load.load(replaced)
        elif type_of_file.lstrip(".") in {"svg"}:
            return ET.fromstring(file_content)
        else:
            result = json.load(StringIO(file_content))
            # It's possible to that the result will be `str` after loading it. In this case, we need to load it again.
            return json.loads(result) if isinstance(result, str) else result
    except Exception as e:
        logger.error(
            f"{file_path} has a structure issue of file type {type_of_file}\n{e}"
        )
        if raise_on_error:
            raise
        return {}


def get_file_or_remote(file_path: Path, clear_cache=False):
    content_path = get_content_path()
    relative_file_path = None
    if file_path.is_absolute():
        absolute_file_path = file_path
        try:
            relative_file_path = file_path.relative_to(content_path)
        except ValueError:
            logger.debug(
                f"{file_path} is not a subpath of {content_path}. If the file does not exists locally, it could not be fetched."
            )
    else:
        absolute_file_path = content_path / file_path
        relative_file_path = file_path
    try:
        return get_file(absolute_file_path, clear_cache=clear_cache)
    except FileNotFoundError:
        logger.warning(
            f"Could not read/find {absolute_file_path} locally, fetching from remote"
        )
        if not relative_file_path:
            logger.error(
                f"The file path provided {file_path} is not a subpath of {content_path}. could not fetch from remote."
            )
            raise
        return get_remote_file(str(relative_file_path))


def get_yaml(
    file_path: str | Path,
    cache_clear=False,
    keep_order: bool = False,
    git_sha: Optional[str] = None,
):
    if cache_clear:
        get_file.cache_clear()
    return get_file(
        file_path, clear_cache=cache_clear, keep_order=keep_order, git_sha=git_sha
    )


def get_json(file_path: str | Path, cache_clear=False, git_sha: Optional[str] = None):
    if cache_clear:
        get_file.cache_clear()
    return get_file(file_path, clear_cache=cache_clear, git_sha=git_sha)


def get_script_or_integration_id(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        commonfields = data_dictionary.get("commonfields", {})
        return commonfields.get(
            "id",
            [
                "-",
            ],
        )


def get_api_module_integrations_set(changed_api_modules: Set, integration_set: Set):
    integrations_set = list()
    for integration in integration_set:
        integration_data = list(integration.values())[0]
        if changed_api_modules & set(integration_data.get("api_modules", [])):
            integrations_set.append(integration_data)
    return integrations_set


def get_api_module_ids(file_list) -> Set:
    """Extracts APIModule IDs from the file list"""
    api_module_set = set()
    if file_list:
        for pf in file_list:
            parent = pf
            while f"/{API_MODULES_PACK}/Scripts/" in parent:
                parent = get_parent_directory_name(parent, abs_path=True)
                if f"/{API_MODULES_PACK}/Scripts/" in parent:
                    pf = parent
            if parent != pf:
                api_module_set.add(Path(pf).name)
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
            return data.get("commonfields", {}).get("id", "")
        elif content_entity == LAYOUTS_DIR:
            # typeId is for old format layouts, id is for layoutscontainers
            return data.get("typeId", data.get("id", ""))
        else:
            return data.get("id", "")

    except AttributeError:
        raise ValueError(
            f"Could not retrieve id from file of type {content_entity} - make sure the file structure is "
            f"valid"
        )


def collect_ids(file_path):
    """Collect id mentioned in file_path"""
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        return data_dictionary.get("id", "-")


def get_from_version(file_path):
    data_dictionary = (
        get_yaml(file_path) if file_path.endswith("yml") else get_json(file_path)
    )

    if not isinstance(data_dictionary, dict):
        raise ValueError("yml file returned is not of type dict")

    if data_dictionary:
        from_version = (
            data_dictionary.get("fromversion")
            if "fromversion" in data_dictionary
            else data_dictionary.get("fromVersion", "")
        )

        if not from_version:
            logger.warning(f"fromversion/fromVersion was not found in '{file_path}'")
            return ""

        if not re.match(r"^\d{1,2}\.\d{1,2}\.\d{1,2}$", from_version):
            raise ValueError(
                f'{file_path} fromversion is invalid "{from_version}". '
                'Should be of format: "x.x.x". for example: "4.5.0"'
            )

        return from_version

    return ""


def get_to_version(file_path):
    data_dictionary = get_yaml(file_path)

    if data_dictionary:
        to_version = data_dictionary.get("toversion", DEFAULT_CONTENT_ITEM_TO_VERSION)
        if not re.match(r"^\d{1,2}\.\d{1,2}\.\d{1,2}$", to_version):
            raise ValueError(
                f'{file_path} toversion is invalid "{to_version}". '
                'Should be of format: "x.x.x". for example: "4.5.0"'
            )

        return to_version

    return DEFAULT_CONTENT_ITEM_TO_VERSION


def str2bool(v):
    """
    Deprecated. Use string_to_bool instead
    """
    return string_to_bool(v, default_when_empty=False)


def to_dict(obj):
    if isinstance(obj, Enum):
        return obj.name

    if not hasattr(obj, "__dict__"):
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
        return os.path.join(dir_name, "CHANGELOG.md")

    # We got the CHANGELOG file to get its release notes
    if file_path.endswith("CHANGELOG.md"):
        return file_path

    # outside of packages, change log file will include the original file name.
    file_name = Path(file_path).name
    return os.path.join(dir_name, os.path.splitext(file_name)[0] + "_CHANGELOG.md")


def old_get_latest_release_notes_text(rn_path):
    if not Path(rn_path).is_file():
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
        new_rn = rn.replace(UNRELEASE_HEADER, "")  # type: ignore

    return new_rn if new_rn else None


def find_pack_folder(path: Path) -> Path:
    """
    Finds the pack folder.
    """

    if "Packs" not in path.parts:
        raise ValueError(f"Could not find a pack for {str(path)}")
    if path.parent.name == "Packs":
        return path
    return path.parents[len(path.parts) - (path.parts.index("Packs")) - 3]


def get_release_notes_file_path(file_path):
    """
    Accepts file path which is alleged to contain release notes. Validates that the naming convention
    is followed. If the file identified does not match the naming convention, error is returned.
    :param file_path: str - File path of the suspected release note.
    :return: file_path: str - Validated release notes path.
    """
    if file_path is None:
        logger.info("[yellow]Release notes were not found.[/yellow]")
        return None
    else:
        if bool(re.search(r"\d{1,2}_\d{1,2}_\d{1,2}\.md", file_path)):
            return file_path
        else:
            logger.info(
                f"[yellow]Unsupported file type found in ReleaseNotes directory - {file_path}[/yellow]"
            )
            return None


def get_latest_release_notes_text(rn_path):
    if rn_path is None:
        logger.info("[yellow]Path to release notes not found.[/yellow]")
        rn = None
    else:
        try:
            with open(rn_path) as f:
                rn = f.read()

            if not rn:
                logger.info(
                    f"[red]Release Notes may not be empty. Please fill out correctly. - {rn_path}[/red]"
                )
                return ""
        except OSError:
            return ""

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
        formatted_version = "0.0.0"
    elif len(version.split(".")) == 1:
        formatted_version = f"{version}.0.0"
    elif len(version.split(".")) == 2:
        formatted_version = f"{version}.0"

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

    _v1, _v2 = Version(v1), Version(v2)
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
    default_pack_known_words = [
        get_pack_name(file_path),
    ]
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
    integrations_dir_path = os.path.join(
        PACKS_DIR, get_pack_name(file_path), INTEGRATIONS_DIR
    )
    command_names: Set[str] = set()
    if not glob.glob(integrations_dir_path):
        return command_names

    found_integrations: List[str] = os.listdir(integrations_dir_path)
    if found_integrations:
        for integration in found_integrations:
            command_names.add(integration)

            integration_path_full = os.path.join(
                integrations_dir_path, integration, f"{integration}.yml"
            )
            yml_dict = get_yaml(integration_path_full)
            commands = yml_dict.get("script", {}).get("commands", [])
            command_names = command_names.union(
                {command.get("name") for command in commands}
            )

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
            if script.endswith(".md"):
                continue  # in case the script is in the old version of CommonScripts - JS code, ignore the md file
            elif script.endswith(".yml"):
                # in case the script is in the old version of CommonScripts - JS code, only yml exists not in a dir
                script_path_full = os.path.join(scripts_dir_path, script)
            else:
                script_path_full = os.path.join(
                    scripts_dir_path, script, f"{script}.yml"
                )
            try:
                yml_dict = get_yaml(script_path_full)
                scripts_names.add(yml_dict.get("name"))
            except FileNotFoundError:
                # we couldn't load the script as the path is not fit Content convention scripts' names
                scripts_names.add(script)
    return scripts_names


def get_pack_name(file_path: Union[str, Path]):
    """
    extract pack name (folder name) from file path

    Arguments:
        file_path (str): path of a file inside the pack

    Returns:
        pack name (str)
    """
    file_path = Path(file_path)
    parts = file_path.parts
    if PACKS_FOLDER not in parts:
        return None
    pack_name_index = parts.index(PACKS_FOLDER) + 1
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

        if not path.startswith("Packs/"):
            continue

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
    return os.path.join(get_content_path(), PACKS_DIR, pack_name)  # type: ignore


def pack_name_to_posix_path(pack_name):
    return PosixPath(pack_name_to_path(pack_name))


def get_pack_ignore_file_path(pack_name):
    return os.path.join(get_content_path(), PACKS_DIR, pack_name, PACKS_PACK_IGNORE_FILE_NAME)  # type: ignore


def get_test_playbook_id(test_playbooks_list: list, tpb_path: str) -> Tuple:  # type: ignore
    """

    Args:
        test_playbooks_list: The test playbook list from id_set
        tpb_path: test playbook path.

    Returns (Tuple): test playbook name and pack.

    """
    for test_playbook_dict in test_playbooks_list:
        test_playbook_id = list(test_playbook_dict.keys())[0]
        test_playbook_path = test_playbook_dict[test_playbook_id].get("file_path")
        test_playbook_pack = test_playbook_dict[test_playbook_id].get("pack")
        if not test_playbook_path or not test_playbook_pack:
            continue

        if tpb_path in test_playbook_path:
            return test_playbook_id, test_playbook_pack
    return None, None


def get_pack_ignore_content(pack_name: str) -> Union[ConfigParser, None]:
    """
    Args:
        pack_name: a pack name from which to get the pack ignore config.

    Returns:
        ConfigParser | None: config parser object in case of success, None otherwise.
    """
    _pack_ignore_file_path = Path(get_pack_ignore_file_path(pack_name))
    if _pack_ignore_file_path.exists():
        try:
            config = ConfigParser(allow_no_value=True)
            config.read(_pack_ignore_file_path)
            return config
        except MissingSectionHeaderError:
            logger.exception(
                f"Error when retrieving the content of {_pack_ignore_file_path}"
            )
            return None
    logger.warning(
        f"[red]Could not find pack-ignore file at path {_pack_ignore_file_path} for pack {pack_name}[/red]"
    )
    return None


def get_ignore_pack_skipped_tests(
    pack_name: str, modified_packs: set, id_set: dict
) -> set:
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
    test_playbooks = id_set.get("TestPlaybooks", {})

    # pack_ignore_path = get_pack_ignore_file_path(pack_name)
    if pack_name in modified_packs and (config := get_pack_ignore_content(pack_name)):
        # go over every file in the config
        for section in filter(
            lambda section: section.startswith("file:"), config.sections()
        ):
            # given section is of type file
            file_name: str = section[5:]
            for key in config[section]:
                if key == "ignore":
                    # group ignore codes to a list
                    file_name_to_ignore_dict[file_name] = str(
                        config[section][key]
                    ).split(",")

    for file_name, ignore_list in file_name_to_ignore_dict.items():
        if any(ignore_code == "auto-test" for ignore_code in ignore_list):
            test_id, test_pack = get_test_playbook_id(test_playbooks, file_name)
            if test_id:
                ignored_tests_set.add(test_id)
    return ignored_tests_set


def get_docker_images_from_yml(script_obj) -> List[str]:
    """
    Gets a yml as dict of the script/integration that lint runs on, and returns a list of all 'dockerimage' values
    in the yml (including 'alt_dockerimages' if the key exist).

    Args:
        script_obj (dict): A yml as dict of the integration/script that lint runs on.

    Returns:
        (List): A list including all the docker images of the integration/script.
    """
    # this makes sure the first docker in the list is the main docker image.
    def_docker_image = DEF_DOCKER
    if script_obj.get("type") == TYPE_PWSH:
        def_docker_image = DEF_DOCKER_PWSH
    imgs = [script_obj.get("dockerimage") or def_docker_image]

    # get additional docker images
    for key in script_obj.keys():
        if "dockerimage" in key and key != "dockerimage":
            if isinstance(script_obj.get(key), str):
                imgs.append(script_obj.get(key))

            elif isinstance(script_obj.get(key), list):
                imgs.extend(script_obj.get(key))

    return imgs


def get_pipenv_dir(py_version, envs_dirs_base):
    """
    Get the direcotry holding pipenv files for the specified python version
    Arguments:
        py_version {float} -- python version as 2.7 or 3.7
    Returns:
        string -- full path to the pipenv dir
    """
    return f"{envs_dirs_base}{int(py_version)}"


def get_dict_from_file(
    path: str,
    raises_error: bool = True,
    clear_cache: bool = False,
    keep_order: bool = True,
) -> Tuple[Dict, Union[str, None]]:
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
            if path.endswith(".yml"):
                return (
                    get_yaml(path, cache_clear=clear_cache, keep_order=keep_order),
                    "yml",
                )
            elif path.endswith(".json"):
                res = get_json(path, cache_clear=clear_cache)
                if isinstance(res, list) and len(res) == 1 and isinstance(res[0], dict):
                    return res[0], "json"
                else:
                    return res, "json"
            elif path.endswith(".py"):
                return {}, "py"
            elif path.endswith(".xif"):
                return {}, "xif"
    except FileNotFoundError:
        if raises_error:
            raise

    return {}, None


@lru_cache
def find_type_by_path(path: Union[str, Path] = "") -> Optional[FileType]:
    """Find FileType value of a path, without accessing the file.
    This function is here as we want to implement lru_cache and we can do it on `find_type`
    as dict is not hashable.

    It's also theoretically faster, as files are not opened.
    """
    path = Path(path)
    if path.suffix == ".md":
        if "README" in path.name:
            return FileType.README
        elif RELEASE_NOTES_DIR in path.parts:
            return FileType.RELEASE_NOTES
        elif "description" in path.name:
            return FileType.DESCRIPTION
        elif path.name.endswith("CHANGELOG.md"):
            return FileType.CHANGELOG

    if path.suffix == ".json":
        if RELEASE_NOTES_DIR in path.parts:
            return FileType.RELEASE_NOTES_CONFIG
        elif LISTS_DIR in os.path.dirname(path):
            return FileType.LISTS
        elif path.parent.name == JOBS_DIR:
            return FileType.JOB
        elif path.name == CONF_JSON_FILE_NAME:
            return FileType.CONF_JSON
        elif INDICATOR_TYPES_DIR in path.parts:
            return FileType.REPUTATION
        elif XSIAM_DASHBOARDS_DIR in path.parts:
            return FileType.XSIAM_DASHBOARD
        elif XSIAM_REPORTS_DIR in path.parts:
            return FileType.XSIAM_REPORT
        elif TRIGGER_DIR in path.parts:
            return FileType.TRIGGER
        elif path.name == PACKS_PACK_META_FILE_NAME:
            return FileType.METADATA
        elif path.name.endswith(XSOAR_CONFIG_FILE):
            return FileType.XSOAR_CONFIG
        elif "CONTRIBUTORS" in path.name:
            return FileType.CONTRIBUTORS
        elif XDRC_TEMPLATE_DIR in path.parts:
            return FileType.XDRC_TEMPLATE
        elif MODELING_RULES_DIR in path.parts and "testdata" in path.stem.casefold():
            return FileType.MODELING_RULE_TEST_DATA
        elif ASSETS_MODELING_RULES_DIR in path.parts and path.stem.casefold().endswith(
            "_schema"
        ):
            return FileType.MODELING_RULE_SCHEMA
        elif MODELING_RULES_DIR in path.parts and path.stem.casefold().endswith(
            "_schema"
        ):
            return FileType.MODELING_RULE_SCHEMA
        elif LAYOUT_RULES_DIR in path.parts:
            return FileType.LAYOUT_RULE
        elif PRE_PROCESS_RULES_DIR in path.parts:
            return FileType.PRE_PROCESS_RULES

    elif (path.stem.endswith("_image") and path.suffix == ".png") or (
        (path.stem.endswith("_dark") or path.stem.endswith("_light"))
        and path.suffix == ".svg"
    ):
        if path.name.endswith("Author_image.png"):
            return FileType.AUTHOR_IMAGE
        elif XSIAM_DASHBOARDS_DIR in path.parts:
            return FileType.XSIAM_DASHBOARD_IMAGE
        elif XSIAM_REPORTS_DIR in path.parts:
            return FileType.XSIAM_REPORT_IMAGE
        return FileType.IMAGE

    elif path.suffix == ".png" and DOC_FILES_DIR in path.parts:
        return FileType.DOC_IMAGE

    elif path.suffix == ".ps1":
        return FileType.POWERSHELL_FILE

    elif path.name == ".vulture_whitelist.py":
        return FileType.VULTURE_WHITELIST

    elif path.suffix == ".py":
        return FileType.PYTHON_FILE

    elif path.suffix == ".js":
        return FileType.JAVASCRIPT_FILE

    elif path.suffix == ".xif":
        if ASSETS_MODELING_RULES_DIR in path.parts:
            return FileType.ASSETS_MODELING_RULE_XIF
        if MODELING_RULES_DIR in path.parts:
            return FileType.MODELING_RULE_XIF
        elif PARSING_RULES_DIR in path.parts:
            return FileType.PARSING_RULE_XIF
        return FileType.XIF_FILE

    elif path.suffix == ".yml":
        if path.parts[0] in {".circleci", ".gitlab"}:
            return FileType.BUILD_CONFIG_FILE

        elif path.parent.name == SCRIPTS_DIR and path.name.startswith("script-"):
            # Packs/myPack/Scripts/script-myScript.yml
            return FileType.SCRIPT

        elif (
            path.parent.parent.name == SCRIPTS_DIR
            and path.name == f"{path.parent.name}.yml"
        ):
            # Packs/myPack/Scripts/myScript/myScript.yml
            return FileType.SCRIPT

        elif XDRC_TEMPLATE_DIR in path.parts:
            return FileType.XDRC_TEMPLATE_YML

        elif PARSING_RULES_DIR in path.parts:
            return FileType.PARSING_RULE

        elif MODELING_RULES_DIR in path.parts:
            return FileType.MODELING_RULE

        elif ASSETS_MODELING_RULES_DIR in path.parts:
            return FileType.ASSETS_MODELING_RULE

        elif CORRELATION_RULES_DIR in path.parts:
            return FileType.CORRELATION_RULE

    elif path.name == FileType.PACK_IGNORE:
        return FileType.PACK_IGNORE

    elif path.name == FileType.SECRET_IGNORE:
        return FileType.SECRET_IGNORE

    elif path.parent.name == DOC_FILES_DIR:
        return FileType.DOC_FILE

    elif path.name.lower() == "pipfile":
        return FileType.PIPFILE

    elif path.name.lower() == "pipfile.lock":
        return FileType.PIPFILE_LOCK

    elif path.suffix.lower() == ".ini":
        return FileType.INI

    elif path.suffix.lower() == ".pem":
        return FileType.PEM

    elif (
        path.name.lower()
        in ("commands_example", "commands_examples", "command_examples")
        or path.suffix.lower() == ".txt"
    ):
        return FileType.TXT

    elif path.name == ".pylintrc":
        return FileType.PYLINTRC

    elif path.name == "LICENSE":
        return FileType.LICENSE

    return None


# flake8: noqa: C901


def find_type(
    path: str = "",
    _dict=None,
    file_type: Optional[str] = None,
    ignore_sub_categories: bool = False,
    ignore_invalid_schema_file: bool = False,
    clear_cache: bool = False,
):
    """
    Returns the content file type

    Arguments:
         path (str): a path to the file.
        _dict (dict): file dict representation if exists.
        file_type (str): a string representation of the file type.
        ignore_sub_categories (bool): ignore the sub categories, True to ignore, False otherwise.
        ignore_invalid_schema_file (bool): whether to ignore raising error on invalid schema files,
            True to ignore, False otherwise.
        clear_cache (bool): whether to clear the cache.

    Returns:
        FileType | None: Enum representation of the content file type, None otherwise.
    """
    from demisto_sdk.commands.content_graph.objects import (
        Classifier,
        CorrelationRule,
        Dashboard,
        GenericDefinition,
        GenericField,
        GenericModule,
        GenericType,
        IncidentField,
        IncidentType,
        IndicatorField,
        IndicatorType,
        Integration,
        Job,
        Layout,
        LayoutRule,
        Mapper,
        ModelingRule,
        ParsingRule,
        Playbook,
        PreProcessRule,
        Report,
        Script,
        TestPlaybook,
        TestScript,
        Trigger,
        Widget,
        Wizard,
        XDRCTemplate,
        XSIAMDashboard,
        XSIAMReport,
    )
    from demisto_sdk.commands.content_graph.objects import List as List_obj

    type_by_path = find_type_by_path(path)
    if type_by_path:
        return type_by_path
    try:
        if not _dict and not file_type:
            _dict, file_type = get_dict_from_file(
                path, clear_cache=clear_cache, keep_order=False
            )

    except FileNotFoundError:
        # unable to find the file - hence can't identify it
        return None
    except ValueError as err:
        if ignore_invalid_schema_file:
            # invalid file schema
            logger.debug(str(err))
            return None
        raise err

    if (file_type == "yml" or path.lower().endswith(".yml")) and path.lower().endswith(
        "_unified.yml"
    ):
        return FileType.UNIFIED_YML

    if (
        (file_type == "yml" or path.lower().endswith(".yml"))
        and "category" in _dict
        and _dict.get("beta")
        and not ignore_sub_categories
    ):
        return FileType.BETA_INTEGRATION

    if Integration.match(_dict, Path(path)):
        return FileType.INTEGRATION

    if TestScript.match(_dict, Path(path)) and not ignore_sub_categories:
        return FileType.TEST_SCRIPT

    if Script.match(_dict, Path(path)):
        return FileType.SCRIPT

    if TestPlaybook.match(_dict, Path(path)):
        return FileType.TEST_PLAYBOOK

    if Playbook.match(_dict, Path(path)):
        return FileType.PLAYBOOK

    if ParsingRule.match(_dict, Path(path)):
        return FileType.PARSING_RULE

    if MODELING_RULES_DIR in Path(path).parts:
        if ModelingRule.match(_dict, Path(path)):
            return FileType.MODELING_RULE

    if CorrelationRule.match(_dict, Path(path)):
        return FileType.CORRELATION_RULE

    if (file_type == "json" or path.lower().endswith(".json")) and (
        path.lower().endswith("_schema.json") and MODELING_RULES_DIR in Path(path).parts
    ):
        return FileType.MODELING_RULE_SCHEMA

    if Widget.match(_dict, Path(path)):
        return FileType.WIDGET

    if Report.match(_dict, Path(path)):
        return FileType.REPORT

    if GenericType.match(_dict, Path(path)):
        return FileType.GENERIC_TYPE

    if IncidentType.match(_dict, Path(path)):
        return FileType.INCIDENT_TYPE

    # 'regex' key can be found in new reputations files while 'reputations' key is for the old reputations
    # located in reputations.json file.
    if IndicatorType.match(_dict, Path(path)):
        return FileType.REPUTATION

    if (
        (file_type == "json" or path.lower().endswith(".json"))
        and "brandName" in _dict
        and "transformer" in _dict
    ):
        return FileType.OLD_CLASSIFIER

    if Classifier.match(_dict, Path(path)):
        return FileType.CLASSIFIER

    if Mapper.match(_dict, Path(path)):
        return FileType.MAPPER

    if (
        file_type == "json" or path.lower().endswith(".json")
    ) and "canvasContextConnections" in _dict:
        return FileType.CONNECTION

    if (
        ("layout" in _dict or "kind" in _dict)
        and ("kind" in _dict or "typeId" in _dict)
        and Path(path).suffix == ".json"
    ):
        return FileType.LAYOUT

    if isinstance(_dict, dict) and LAYOUT_CONTAINER_FIELDS.intersection(_dict):
        if Layout.match(_dict, Path(path)):
            return FileType.LAYOUTS_CONTAINER

    if Dashboard.match(_dict, Path(path)):
        return FileType.DASHBOARD

    if PreProcessRule.match(_dict, Path(path)):
        return FileType.PRE_PROCESS_RULES

    if GenericModule.match(_dict, Path(path)):
        return FileType.GENERIC_MODULE

    if GenericDefinition.match(_dict, Path(path)):
        return FileType.GENERIC_DEFINITION

    if Job.match(_dict, Path(path)):
        return FileType.JOB

    if Wizard.match(_dict, Path(path)):
        return FileType.WIZARD

    if XSIAMDashboard.match(_dict, Path(path)):
        return FileType.XSIAM_DASHBOARD

    if XSIAMReport.match(_dict, Path(path)):
        return FileType.XSIAM_REPORT

    if Trigger.match(_dict, Path(path)):
        return FileType.TRIGGER

    if XDRCTemplate.match(_dict, Path(path)):
        return FileType.XDRC_TEMPLATE

    if LayoutRule.match(_dict, Path(path)):
        return FileType.LAYOUT_RULE

    if List_obj.match(_dict, Path(path)):
        return FileType.LISTS

    # When using it for all files validation- sometimes 'id' can be integer
    if GenericField.match(_dict, Path(path)):
        return FileType.GENERIC_FIELD

    if IncidentField.match(_dict, Path(path)):
        return FileType.INCIDENT_FIELD

    if IndicatorField.match(_dict, Path(path)):
        return FileType.INDICATOR_FIELD

    return None


def get_common_server_path(env_dir):
    common_server_dir = get_common_server_dir(env_dir)
    return os.path.join(common_server_dir, "CommonServerPython.py")


def get_common_server_path_pwsh(env_dir):
    common_server_dir = get_common_server_dir_pwsh(env_dir)
    return os.path.join(common_server_dir, "CommonServerPowerShell.ps1")


def _get_common_server_dir_general(env_dir, name):
    common_server_pack_path = os.path.join(env_dir, "Packs", "Base", "Scripts", name)

    return common_server_pack_path


def get_common_server_dir(env_dir):
    return _get_common_server_dir_general(env_dir, "CommonServerPython")


def get_common_server_dir_pwsh(env_dir):
    return _get_common_server_dir_general(env_dir, "CommonServerPowerShell")


def is_external_repository() -> bool:
    """
    Returns True if script executed from private repository

    """
    try:
        git_repo = GitUtil().repo
        private_settings_path = os.path.join(git_repo.working_dir, ".private-repo-settings")  # type: ignore
        return Path(private_settings_path).exists()
    except git.InvalidGitRepositoryError:
        return True


def get_content_id_set() -> dict:
    """Getting the ID Set from official content's bucket"""
    return requests.get(OFFICIAL_CONTENT_ID_SET_PATH).json()


def download_content_graph(
    output_path: Path, marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR
) -> Path:
    """Getting the Content Graph from official content's bucket"""
    if output_path.is_dir():
        output_path = output_path / f"{marketplace.value}.zip"
    output_path.write_bytes(
        requests.get(f"{OFFICIAL_CONTENT_GRAPH_PATH}/{marketplace.value}.zip").content
    )
    return output_path


def get_latest_upload_flow_commit_hash() -> str:
    """Getting the latest commit hash of the upload flow from official content's bucket

    Returns:
        str: the last commit hash of the upload flow
    """
    response_json = requests.get(OFFICIAL_INDEX_JSON_PATH).json()
    if not isinstance(response_json, dict):
        raise ValueError(
            f"The index.json file is not in the expected format: {response_json}"
        )
    last_commit = response_json.get("commit")
    if not last_commit:
        raise ValueError("The latest commit hash was not found in the index.json file")
    return last_commit


def get_content_path(relative_path: Optional[Path] = None) -> Path:
    """Get abs content path, from any CWD
    Args:
        Optional[Path]: Path to file or folder in content repo. If not provided, the environment variable or cwd will be used.
    Returns:
        str: Absolute content path
    """
    # ValueError can be suppressed since as default, the environment variable or git.Repo can be used to find the content path.
    with contextlib.suppress(ValueError):
        if relative_path:
            return (
                relative_path.absolute().parent
                if relative_path.name == "Packs"
                else find_pack_folder(relative_path.absolute()).parent.parent
            )
    try:
        if content_path := os.getenv("DEMISTO_SDK_CONTENT_PATH"):
            git_repo = GitUtil(Path(content_path), search_parent_directories=False).repo
            logger.debug(f"Using content path: {content_path}")
        else:
            git_repo = GitUtil().repo

        try:
            remote_url = git_repo.remote(name=DEMISTO_GIT_UPSTREAM).urls.__next__()
        except ValueError:
            if not os.getenv("DEMISTO_SDK_IGNORE_CONTENT_WARNING"):
                logger.warning(
                    f"Could not find remote with name {DEMISTO_GIT_UPSTREAM} for repo {git_repo.working_dir}"
                )
            remote_url = ""
        is_fork_repo = "content" in remote_url
        is_external_repo = is_external_repository()

        if not is_fork_repo and not is_external_repo:
            raise git.InvalidGitRepositoryError
        if not git_repo.working_dir:
            return Path.cwd()
        return Path(git_repo.working_dir)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        if not os.getenv("DEMISTO_SDK_IGNORE_CONTENT_WARNING"):
            logger.info(
                "[yellow]Please run demisto-sdk in content repository![/yellow]"
            )
    return Path(".")


def run_command_os(
    command: str, cwd: Union[Path, str], env: Union[os._Environ, dict] = os.environ
) -> Tuple[str, str, int]:
    """Run command in subprocess tty
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
            universal_newlines=True,
        )
        stdout, stderr = process.communicate()
    except OSError as e:
        return "", str(e), 1

    return stdout, stderr, process.returncode


def pascal_case(st: str) -> str:
    """Convert a string to pascal case. Will simply remove spaces and make sure the first
    character is capitalized

    Arguments:
        st {str} -- string to convert

    Returns:
        str -- converted string
    """
    words = re.findall(r"[a-zA-Z0-9]+", st)
    return "".join("".join([w[0].upper(), w[1:]]) for w in words)


def capital_case(st: str) -> str:
    """Capitalize the first letter of each word of a string. The remaining characters are untouched.

    Arguments:
        st {str} -- string to convert

    Returns:
        str -- converted string
    """
    if len(st) >= 1:
        words = st.split()
        return " ".join([f"{s[:1].upper()}{s[1:]}" for s in words if len(s) >= 1])
    else:
        return ""


@lru_cache
def get_last_release_version():
    """
    Get latest release tag (xx.xx.xx)

    :return: tag
    """
    tags = run_command("git tag").split("\n")
    tags = [tag for tag in tags if re.match(r"\d+\.\d+\.\d+", tag) is not None]
    tags.sort(key=Version, reverse=True)

    return tags[0]


def is_file_from_content_repo(file_path: str) -> Tuple[bool, str]:
    """Check if an absolute file_path is part of content repo.
    Args:
        file_path (str): The file path which is checked.
    Returns:
        bool: if file is part of content repo.
        str: relative path of file in content repo.
    """
    try:
        git_repo = GitUtil().repo
        remote_url = git_repo.remote().urls.__next__()
        is_fork_repo = "content" in remote_url
        is_external_repo = is_external_repository()

        if not is_fork_repo and not is_external_repo:
            return False, ""
        content_path_parts = Path(git_repo.working_dir).parts  # type: ignore
        input_path_parts = Path(file_path).parts
        input_path_parts_prefix = input_path_parts[: len(content_path_parts)]
        if content_path_parts == input_path_parts_prefix:
            return True, "/".join(input_path_parts[len(content_path_parts) :])
        else:
            return False, ""

    except Exception as e:
        logger.info(f"Unable to identify the repository: {e}")
        return False, ""


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
    if file_extension not in [".yml", ".json", ".md"]:
        return True
    if any(
        ignore_pattern in file_path.lower()
        for ignore_pattern in ALL_FILES_VALIDATION_IGNORE_WHITELIST
    ):
        return True
    # Ignoring changelog and description files since these are checked on the integration validation
    if "changelog" in file_path.lower() or "description" in file_path.lower():
        return True
    # unified files should not be validated
    if file_path.endswith("_unified.yml"):
        return True
    return False


def is_test_config_match(
    test_config: dict,
    test_playbook_id: str = "",
    integration_id: str = "",
    script_id: str = "",
) -> bool:
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
        script_id: A script ID.
    If both test_playbook_id and integration_id are given will look for a match of both, else will look for match
    of either test playbook id or integration id or script id.
    Returns:
        True if the test configuration contains the test playbook and the content item or False if not
    """
    test_playbook_match = test_playbook_id == test_config.get("playbookID")
    test_integrations = test_config.get("integrations")
    test_scripts = test_config.get("scripts")
    if isinstance(test_integrations, list):
        integration_match = any(
            test_integration
            for test_integration in test_integrations
            if test_integration == integration_id
        )
    else:
        integration_match = test_integrations == integration_id

    if isinstance(test_scripts, list):
        scripts_match = any(
            test_script for test_script in test_scripts if test_script == script_id
        )
    else:
        scripts_match = test_scripts == script_id

    # If both playbook id and integration id are given
    if integration_id and test_playbook_id:
        return test_playbook_match and integration_match

    # If only integration id is given
    if integration_id:
        return integration_match

    # If only test playbook is given
    if test_playbook_id:
        return test_playbook_match

    if script_id:
        return scripts_match

    return False


def is_content_item_dependent_in_conf(test_config, file_type) -> bool:
    """Check if a line from conf have multiple integration/scripts dependent on the TPB.
        - if the TPB checks only one integration/script it is independent.
          For example: {"integrations": ["PagerDuty v2"], "playbookID": "PagerDuty Test"}.
        - if the TPB checks more then one integration/script it is dependent.
          For example: {"integrations": ["PagerDuty v2", "PagerDuty v3"], "playbookID": "PagerDuty Test"}.
    Args:
        test_config (dict): The dict in the conf file.
        file_type (str): The file type, can be integrations, scripts or playbook.

    Returns:
        bool: The return value. True for dependence, False otherwise.
    """
    integrations_list = test_config.get("integrations", [])
    integrations_list = (
        integrations_list
        if isinstance(integrations_list, list)
        else [integrations_list]
    )
    scripts_list = test_config.get("scripts", [])
    scripts_list: list = (
        scripts_list if isinstance(scripts_list, list) else [scripts_list]
    )
    if file_type == "integration":
        return len(integrations_list) > 1
    if file_type == "script":
        return len(scripts_list) > 1
    # if the file_type is playbook or testplaybook in the conf.json it does not dependent on any other content
    elif file_type == "playbook":
        return False
    return True


def search_and_delete_from_conf(
    conf_json_tests: list,
    content_item_id: str,
    file_type: str,
    test_playbooks: list,
    no_test_playbooks_explicitly: bool,
) -> List[dict]:
    """Return all test section from conf.json file without the deprecated content item.

    Args:
        conf_json_tests (int): The dict in the conf file.
        content_item_id (str): The  content item id.
        file_type (str): The file type, can be integrations, scripts or playbook.
        test_playbooks (list): A list of related test playbooks.
        no_test_playbooks_explicitly (bool): True if there are related TPB, False otherwise.

    Returns:
        bool: The return value. True for dependence, False otherwise.
    """
    keyword = ""
    test_registered_in_conf_json = []
    # If the file type we are deprecating is a integration - there are TBP related to the yml
    if file_type == "integration":
        keyword = "integration_id"

    elif file_type == "playbook":
        keyword = "test_playbook_id"

    elif file_type == "script":
        keyword = "script_id"

    test_registered_in_conf_json.extend(
        [
            test_config
            for test_config in conf_json_tests
            if is_test_config_match(test_config, **{keyword: content_item_id})
        ]
    )
    if not no_test_playbooks_explicitly:
        for test in test_playbooks:
            if test not in list(
                map(lambda x: x["playbookID"], test_registered_in_conf_json)
            ):
                test_registered_in_conf_json.extend(
                    [
                        test_config
                        for test_config in conf_json_tests
                        if is_test_config_match(test_config, test_playbook_id=test)
                    ]
                )
    # remove the line from conf.json
    if test_registered_in_conf_json:
        for test_config in test_registered_in_conf_json:
            if file_type == "playbook" and test_config in conf_json_tests:
                conf_json_tests.remove(test_config)
            elif (
                test_config in conf_json_tests
                and not is_content_item_dependent_in_conf(test_config, file_type)
            ):
                conf_json_tests.remove(test_config)
            elif test_config in conf_json_tests:
                if content_item_id in (test_config.get("integrations", [])):
                    test_config.get("integrations").remove(content_item_id)
                if content_item_id in (test_config.get("scripts", [])):
                    test_config.get("scripts").remove(content_item_id)

    return conf_json_tests


def get_not_registered_tests(
    conf_json_tests: list, content_item_id: str, file_type: str, test_playbooks: list
) -> list:
    """
    Return all test playbooks that are not configured in conf.json file
    Args:
        conf_json_tests: the 'tests' value of 'conf.json file
        content_item_id: A content item ID, could be a script, an integration or a playbook.
        file_type: The file type, could be an integration or a playbook.
        test_playbooks: The yml file's list of test playbooks.

    Returns:
        A list of TestPlaybooks not configured
    """
    not_registered_tests = []
    for test in test_playbooks:
        if file_type == "playbook":
            test_registered_in_conf_json = any(
                test_config
                for test_config in conf_json_tests
                if is_test_config_match(test_config, test_playbook_id=test)
            )
        else:
            test_registered_in_conf_json = any(
                test_config
                for test_config in conf_json_tests
                if is_test_config_match(test_config, integration_id=content_item_id)
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
        return file_content.get("id", "")
    elif file_type in ID_IN_COMMONFIELDS:
        return file_content.get("commonfields", {}).get("id")
    elif file_type == FileType.LAYOUT_RULE:
        return file_content.get("rule_id", "")
    return file_content.get("trigger_id", "")


def is_path_of_integration_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == INTEGRATIONS_DIR


def is_path_of_script_directory(path: str) -> bool:
    """Returns true if directory is script directory false if not."""
    return Path(path).name == SCRIPTS_DIR


def is_path_of_playbook_directory(path: str) -> bool:
    """Returns true if directory is playbook directory false if not."""
    return Path(path).name == PLAYBOOKS_DIR


def is_path_of_test_playbook_directory(path: str) -> bool:
    """Returns true if directory is test_playbook directory false if not."""
    return Path(path).name == TEST_PLAYBOOKS_DIR


def is_path_of_report_directory(path: str) -> bool:
    """Returns true if directory is report directory false if not."""
    return Path(path).name == REPORTS_DIR


def is_path_of_dashboard_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == DASHBOARDS_DIR


def is_path_of_widget_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == WIDGETS_DIR


def is_path_of_incident_field_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == INCIDENT_FIELDS_DIR


def is_path_of_incident_type_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == INCIDENT_TYPES_DIR


def is_path_of_indicator_field_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == INDICATOR_FIELDS_DIR


def is_path_of_layout_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == LAYOUTS_DIR


def is_path_of_pre_process_rules_directory(path: str) -> bool:
    """Returns true if directory is pre-processing rules directory, false if not."""
    return Path(path).name == PRE_PROCESS_RULES_DIR


def is_path_of_lists_directory(path: str) -> bool:
    return Path(path).name == LISTS_DIR


def is_path_of_classifier_directory(path: str) -> bool:
    """Returns true if directory is integration directory false if not."""
    return Path(path).name == CLASSIFIERS_DIR


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
    return Path(parent_dir_name).name


def get_code_lang(file_data: dict, file_entity: str) -> str:
    """
    Returns content item's code language (python / javascript).
    :param file_data: The file data
    :param file_entity: The file entity
    :return: The code language
    """
    if file_entity == INTEGRATIONS_DIR:
        return file_data.get("script", {}).get("type", "")
    elif file_entity == SCRIPTS_DIR:
        return file_data.get("type", {})
    return ""


def camel_to_snake(camel: str) -> str:
    """
    Converts camel case (CamelCase) strings to snake case (snake_case) strings.
    Args:
        camel (str): The camel case string.

    Returns:
        str: The snake case string.
    """
    camel_to_snake_pattern = re.compile(r"(?<!^)(?=[A-Z][a-z])")
    snake = camel_to_snake_pattern.sub("_", camel).lower()
    return snake


def open_id_set_file(id_set_path):
    id_set = {}
    try:
        with open(id_set_path) as id_set_file:
            id_set = json.load(id_set_file)
    except OSError:
        logger.info("[yellow]Could not open id_set file[/yellow]")
        raise
    finally:
        return id_set


def get_demisto_version(client: demisto_client) -> Version:
    """
    Args:
        demisto_client: A configured demisto_client instance

    Returns:
        the server version of the Demisto instance.
    """
    try:
        resp = client.generic_request("/about", "GET")
        about_data = json.loads(resp[0].replace("'", '"'))
        return Version(Version(about_data.get("demistoVersion")).base_version)
    except Exception as e:
        logger.debug(f"Failed to fetch server version. Error: {e}")
        logger.warning(
            "Could not parse server version, please make sure the environment is properly configured."
        )
        return Version("0")


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
        if arg[0] == "[" and arg[-1] == "]":
            return json.loads(arg)
        return [s.strip() for s in arg.split(separator)]
    return [arg]


def get_file_version_suffix_if_exists(
    current_file: Dict, check_in_display: bool = False
) -> Optional[str]:
    """
    Checks if current YML file name is versioned or no, e.g, ends with v<number>.
    Args:
        current_file (Dict): Dict representing YML data of an integration or script.
        check_in_display (bool): Whether to get name by 'display' field or not (by 'name' field).

    Returns:
        (Optional[str]): Number of the version as a string, if the file ends with version suffix. None otherwise.
    """
    versioned_file_regex = r"v([0-9]+)$"
    name = current_file.get("display") if check_in_display else current_file.get("name")
    if not name:
        return None
    matching_regex = re.findall(versioned_file_regex, name.lower())
    if matching_regex:
        return matching_regex[-1]
    return None


def get_all_incident_and_indicator_fields_from_id_set(id_set_file, entity_type):
    fields_list = []
    for item in ["IncidentFields", "IndicatorFields"]:
        all_item_fields = id_set_file.get(item)
        for item_field in all_item_fields:
            for field, field_info in item_field.items():
                if entity_type == "mapper" or entity_type == "old classifier":
                    fields_list.append(field_info.get("name", ""))
                    fields_list.append(
                        field.replace("incident_", "").replace("indicator_", "")
                    )
                elif entity_type == "layout":
                    fields_list.append(
                        field.replace("incident_", "").replace("indicator_", "")
                    )
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
        "xdrctemplate": "XDRCTemplate",
        "layoutrule": "layoutRule",
    }

    return f"{converter.get(item_type, item_type)}s"


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
    content_items = pack_info_from_id_set.get("ContentItems", {})
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
    if hasattr(var, "items"):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                yield from extract_multiple_keys_from_dict(key, v)
            elif isinstance(v, list):
                for d in v:
                    yield from extract_multiple_keys_from_dict(key, d)


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
    return ""


@lru_cache
def get_file_displayed_name(file_path):
    """Gets the file name that is displayed in the UI by the file's path.
    If there is no displayed name - returns the file name"""
    file_type = find_type(file_path)
    if FileType.INTEGRATION == file_type:
        return get_yaml(file_path).get("display")
    elif file_type in [
        FileType.SCRIPT,
        FileType.TEST_SCRIPT,
        FileType.PLAYBOOK,
        FileType.TEST_PLAYBOOK,
    ]:
        return get_yaml(file_path).get("name")
    elif file_type in [
        FileType.MAPPER,
        FileType.CLASSIFIER,
        FileType.INCIDENT_FIELD,
        FileType.INCIDENT_TYPE,
        FileType.INDICATOR_FIELD,
        FileType.LAYOUTS_CONTAINER,
        FileType.PRE_PROCESS_RULES,
        FileType.DASHBOARD,
        FileType.WIDGET,
        FileType.REPORT,
        FileType.JOB,
        FileType.WIZARD,
    ]:
        res = get_json(file_path)
        return res.get("name") if isinstance(res, dict) else res[0].get("name")
    elif file_type == FileType.OLD_CLASSIFIER:
        return get_json(file_path).get("brandName")
    elif file_type == FileType.LAYOUT:
        return get_json(file_path).get("TypeName")
    elif file_type == FileType.REPUTATION:
        return get_json(file_path).get("id")
    else:
        return Path(file_path).name


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
    context_section_pattern = (
        r"\| *\*\*Path\*\* *\| *\*\*Type\*\* *\| *\*\*Description\*\* *\|.(.*?)#{3,5}"
    )
    # the pattern to get the value in the first column under the outputs table:
    context_path_pattern = r"\| *(\S.*?\S) *\| *[^\|]* *\| *[^\|]* *\|"
    readme_content += (
        "### "  # mark end of file so last pattern of regex will be recognized.
    )
    commands = yml_dict.get("script") or {}

    # handles scripts
    if not commands:
        return different_contexts
    commands = commands.get("commands", [])
    for command in commands:
        command_name = command.get("name")

        # Gets all context path in the relevant command section from README file
        command_section_pattern = rf" Base Command..`{command_name}`.(.*?)\n### "  # pattern to get command section
        command_section = re.findall(command_section_pattern, readme_content, re.DOTALL)
        if not command_section:
            continue
        if not command_section[0].endswith("###"):
            command_section[
                0
            ] += "###"  # mark end of file so last pattern of regex will be recognized.
        context_section = re.findall(
            context_section_pattern, command_section[0], re.DOTALL
        )
        if not context_section:
            context_path_in_command = set()
        else:
            context_path_in_command = set(
                re.findall(context_path_pattern, context_section[0], re.DOTALL)
            )

            # remove the header line ---- (could be of any length)
            for path in context_path_in_command:
                if not path.replace("-", ""):
                    context_path_in_command.remove(path)
                    break

        # handles cases of old integrations with context in 'important' section
        if "important" in command:
            command.pop("important")

        # Gets all context path in the relevant command section from YML file
        existing_context_in_yml = set(
            extract_multiple_keys_from_dict("contextPath", command)
        )

        # finds diff between YML and README
        only_in_yml_paths = existing_context_in_yml - context_path_in_command
        only_in_readme_paths = context_path_in_command - existing_context_in_yml
        if only_in_yml_paths or only_in_readme_paths:
            different_contexts[command_name] = {
                "only in yml": only_in_yml_paths,
                "only in readme": only_in_readme_paths,
            }

    return different_contexts


def write_dict(
    path: Union[Path, str],
    data: Dict,
    handler: Optional[XSOAR_Handler] = None,
    indent: int = 0,
    sort_keys: bool = False,
    **kwargs,
):
    """
    Write unicode content into a json/yml file.
    """
    path = Path(path)
    if not handler:
        suffix = path.suffix.lower()
        if suffix == ".json":
            handler = json
        elif suffix in {".yaml", ".yml"}:
            handler = yaml
        else:
            raise ValueError(f"The file {path} is neither json/yml")

    safe_write_unicode(
        lambda f: handler.dump(data, f, indent, sort_keys, **kwargs), path  # type: ignore[union-attr]
    )


def to_kebab_case(s: str):
    """
    Scan File => scan-file
    Scan File- => scan-file
    *scan,file => scan-file
    Scan     File => scan-file

    """
    if s:
        new_s = s.lower()
        new_s = re.sub("[ ,.-]+", "-", new_s)
        new_s = re.sub("[^A-Za-z0-9-]+", "", new_s)
        m = re.search("[a-z0-9]+(-[a-z0-9]+)*", new_s)
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
        if re.search(r"^[A-Z][a-z]+(?:[A-Z][a-z]+)*$", s):
            return s

        new_s = s.lower()
        new_s = re.sub(r"[ -\.]+", "-", new_s)
        new_s = "".join([t.title() for t in new_s.split("-")])
        new_s = re.sub(r"[^A-Za-z0-9]+", "", new_s)

        return new_s

    return s


def get_approved_usecases() -> list:
    """Gets approved list of usecases from content master

    Returns:
        List of approved usecases
    """
    return get_remote_file(
        "Tests/Marketplace/approved_usecases.json",
        git_content_config=GitContentConfig(
            repo_name=GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        ),
    ).get("approved_list", [])


def get_pack_metadata(file_path: str) -> dict:
    """Get the pack_metadata dict, of the pack containing the given file path.

    Args:
        file_path(str): file path

    Returns: pack_metadata of the pack, that source_file related to,
        on failure returns {}

    """
    pack_path = file_path if PACKS_DIR in file_path else os.path.realpath(__file__)
    match = re.search(rf".*{PACKS_DIR}[/\\]([^/\\]+)[/\\]?", pack_path)
    directory = match.group() if match else ""

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
    return Path(input_path).parent.name == PACKS_DIR


def is_xsoar_supported_pack(file_path: str) -> bool:
    """
    Takes a path to a file and returns a boolean indicating
    whether this file belongs to an XSOAR-supported Pack.

    Args:
        - `file_path` (`str`): The path of the file.

    Returns:
        - `bool`
    """

    return get_pack_metadata(file_path).get(PACK_METADATA_SUPPORT) == XSOAR_SUPPORT


def get_relative_path_from_packs_dir(file_path: str) -> str:
    """Get the relative path for a given file_path starting in the Packs directory"""
    if PACKS_DIR not in file_path or file_path.startswith(PACKS_DIR):
        return file_path

    return file_path[file_path.find(PACKS_DIR) :]


def is_uuid(s: str) -> Optional[Match]:
    """Checks whether given string is a UUID

    Args:
         s (str): The string to check if it is a UUID

    Returns:
        Match: Returns the match if given string is a UUID, otherwise None
    """
    return re.match(UUID_REGEX, s)


def get_release_note_entries(version="") -> list:
    """
    Gets the release notes entries for the current version.

    Args:
        version: The current demisto-sdk version.

    Return:
        list: A list of the release notes given from the CHANGELOG file.
    """

    changelog_file_content = (
        get_remote_file(
            full_file_path="CHANGELOG.md",
            return_content=True,
            git_content_config=GitContentConfig(repo_name="demisto/demisto-sdk"),
        )
        .decode("utf-8")
        .split("\n")
    )

    if not version or "dev" in version:
        version = "Unreleased"

    if f"## {version}" not in changelog_file_content:
        return []

    result = changelog_file_content[changelog_file_content.index(f"## {version}") + 1 :]
    result = result[: result.index("")]

    return result


def get_current_usecases() -> list:
    """Gets approved list of usecases from current branch (only in content repo).

    Returns:
        List of approved usecases from current branch
    """
    if not is_external_repository():
        approved_usecases_json, _ = get_dict_from_file(
            "Tests/Marketplace/approved_usecases.json"
        )
        return approved_usecases_json.get("approved_list", [])
    return []


def get_approved_tags_from_branch() -> Dict[str, List[str]]:
    """Gets approved list of tags from current branch (only in content repo).

    Returns:
        Dict of approved tags from current branch
    """
    if not is_external_repository():
        approved_tags_json, _ = get_dict_from_file(
            "Tests/Marketplace/approved_tags.json"
        )
        if isinstance(approved_tags_json.get("approved_list"), list):
            logger.info(
                "[yellow]You are using a deprecated version of the file aproved_tags.json, consider pulling from master"
                " to update it.[/yellow]"
            )
            return {
                "common": approved_tags_json.get("approved_list", []),
                "xsoar": [],
                "marketplacev2": [],
                "xpanse": [],
            }

        return approved_tags_json.get("approved_list", {})
    return {}


def get_current_categories() -> list:
    """Gets approved list of categories from current branch (only in content repo).

    Returns:
        List of approved categories from current branch
    """
    if is_external_repository():
        return []
    try:
        approved_categories_json, _ = get_dict_from_file(
            "Tests/Marketplace/approved_categories.json"
        )
    except FileNotFoundError:
        logger.warning(
            "File approved_categories.json was not found. Getting from remote."
        )
        approved_categories_json = get_remote_file(
            "Tests/Marketplace/approved_categories.json"
        )
    return approved_categories_json.get("approved_list", [])


@contextmanager
def suppress_stdout():
    """
    Temporarily suppress console output without effecting error outputs.
    Example of use:

        with suppress_stdout():
            logger.info('This message will not be printed')
        logger.info('This message will be printed')
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
        definition_id = file_dictionary["definitionId"]
        generic_def_path = os.path.join(pack_path, "GenericDefinitions")
        file_names_lst = os.listdir(generic_def_path)
        for file in file_names_lst:
            if str.find(file, definition_id):
                def_file_path = os.path.join(generic_def_path, file)
                def_file_dictionary = get_json(def_file_path)
                cur_id = def_file_dictionary["id"]
                if cur_id == definition_id:
                    return def_file_dictionary["name"]

        logger.info("Was unable to find the file for definitionId " + definition_id)
        return None

    except (FileNotFoundError, AttributeError):
        logger.info(
            "Error while retrieving definition name for definitionId "
            + definition_id
            + "\n Check file structure and make sure all relevant fields are entered properly"
        )
        return None


def is_iron_bank_pack(file_path):
    metadata = get_pack_metadata(file_path)
    return PACK_METADATA_IRON_BANK_TAG in metadata.get("tags", [])


def get_script_or_sub_playbook_tasks_from_playbook(
    searched_entity_name: str, main_playbook_data: Dict
) -> List[Dict]:
    """Get the tasks data for a task running the searched_entity_name (script/playbook).

    Returns:
        List. A list of dicts representing tasks running the searched_entity_name.
    """
    searched_tasks: List = []
    tasks = main_playbook_data.get("tasks", {})
    if not tasks:
        return searched_tasks

    for task_data in tasks.values():
        task_details = task_data.get("task", {})
        found_entity = searched_entity_name in {
            task_details.get("scriptName"),
            task_details.get("playbookName"),
        }

        if found_entity:
            searched_tasks.append(task_data)

    return searched_tasks


def extract_docker_image_from_text(text: str, with_no_tag: bool = False):
    """
    Strips the docker image version from a given text.

    Args:
        text (str): the text to extract the docker image from
        with_no_tag (bool): whether to return the docker image without its tag,
            for example if True then demisto/tesseract:1.0.0.36078 --> tesseract

    Returns:
        str: The docker image version if exists, otherwise, return None.
    """
    match = re.search(r"(demisto/.+:([0-9]+)(((\.)[0-9]+)+))", text)
    if match:
        docker_image = match.group(1)
        if with_no_tag:
            return docker_image.replace("demisto/", "").split(":")[0]
        return docker_image
    else:
        return None


def get_current_repo() -> Tuple[str, str, str]:
    try:
        git_repo = GitUtil().repo
        parsed_git = giturlparse.parse(git_repo.remotes.origin.url)
        host = parsed_git.host
        if "@" in host:
            host = host.split("@")[1]
        return host, parsed_git.owner, parsed_git.repo
    except git.InvalidGitRepositoryError:
        logger.info("[yellow]git repo is not found[/yellow]")
        return "Unknown source", "", ""


def get_item_marketplaces(
    item_path: str,
    item_data: Dict = None,
    packs: Dict[str, Dict] = None,
    item_type: str = None,
) -> List:
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
        item_data = get_file(item_path)

    # first check, check field 'marketplaces' in the item's file
    marketplaces = item_data.get("marketplaces", [])  # type: ignore

    # second check, check the metadata of the pack
    if not marketplaces:
        if "pack_metadata" in item_path:
            # default supporting marketplace
            marketplaces = [MarketplaceVersions.XSOAR.value]
        else:
            pack_name = get_pack_name(item_path)
            if packs and packs.get(pack_name):
                marketplaces = packs.get(pack_name, {}).get(
                    "marketplaces", [MarketplaceVersions.XSOAR.value]
                )
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
    if (
        PACKS_PACK_META_FILE_NAME in Path(file_path).parts
    ):  # for when the type is pack, the item we get is the metadata path
        metadata_path = file_path
    else:
        metadata_path_parts = get_pack_dir(file_path)
        metadata_path = Path(*metadata_path_parts) / PACKS_PACK_META_FILE_NAME

    try:
        if not (
            marketplaces := get_file(metadata_path, raise_on_error=True).get(
                MARKETPLACE_KEY_PACK_METADATA
            )
        ):
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
        if parts[index] == "Packs":
            return parts[: index + 2]
    return []


@contextmanager
def ProcessPoolHandler() -> ProcessPool:
    """Process pool Handler which terminate all processes in case of Exception.

    Yields:
        ProcessPool: Pebble process pool.
    """
    with ProcessPool(max_workers=cpu_count()) as pool:
        try:
            yield pool
        except Exception:
            logger.info("[red]Gracefully release all resources due to Error...[/red]")
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
            logger.info(f"[red]{e}[/red]")
            raise


def get_api_module_dependencies(pkgs, id_set_path):
    """
    Get all paths to integrations and scripts dependent on api modules that are found in the modified files.
    Args:
        pkgs: the pkgs paths found as modified to run lint on (including the api module files)
        id_set_path: path to id set
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
        script_name = script_info.get("name")
        script_api_modules = script_info.get("api_modules", [])
        if intersection := changed_api_modules & set(script_api_modules):
            logger.debug(f"found script {script_name} dependent on {intersection}")
            using_scripts.extend(list(script.values()))

    for integration in integrations:
        integration_info = list(integration.values())[0]
        integration_name = integration_info.get("name")
        script_api_modules = integration_info.get("api_modules", [])
        if intersection := changed_api_modules & set(script_api_modules):
            logger.debug(
                f"found integration {integration_name} dependent on {intersection}"
            )
            using_integrations.extend(list(integration.values()))

    using_scripts_pkg_paths = [
        Path(script.get("file_path")).parent.absolute() for script in using_scripts
    ]
    using_integrations_pkg_paths = [
        Path(integration.get("file_path")).parent.absolute()
        for integration in using_integrations
    ]
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
        tasks = data.get("tasks")
        for task_num in tasks.keys():
            task = tasks[task_num]
            inner_task = task.get("task")
            task_type = task.get("type")
            if inner_task and task_type == "regular" or task_type == "playbook":
                if inner_task.get("iscommand"):
                    commands.append(inner_task.get("script"))
                else:
                    if task_type == "playbook":
                        scripts_and_pbs.append(inner_task.get("playbookName"))
                    elif inner_task.get("scriptName"):
                        scripts_and_pbs.append(inner_task.get("scriptName"))
        if file_type == FileType.PLAYBOOK:
            playbook_id = get_entity_id_by_entity_type(data, PLAYBOOKS_DIR)
            scripts_and_pbs.append(playbook_id)

    if file_type == FileType.SCRIPT:
        script_id = get_entity_id_by_entity_type(data, SCRIPTS_DIR)
        scripts_and_pbs = [script_id]
        if data.get("dependson"):
            commands = data.get("dependson").get("must", [])

    if file_type == FileType.INTEGRATION:
        integration_commands = data.get("script", {}).get("commands")
        for integration_command in integration_commands:
            commands.append(integration_command.get("name"))

    for command in commands:
        command_parts = command.split("|||")
        if len(command_parts) == 2:
            detailed_commands.append(
                {"id": command_parts[1], "source": command_parts[0]}
            )
        else:
            detailed_commands.append({"id": command_parts[0]})

    return detailed_commands, scripts_and_pbs


def get_url_with_retries(url: str, retries: int, backoff_factor: int = 1, **kwargs):
    kwargs["stream"] = True
    session = requests.Session()
    exception = Exception()
    for i in range(retries):
        logger.debug(f"attempting to get {url}")
        response = session.get(url, **kwargs)
        try:
            response.raise_for_status()
        except HTTPError as error:
            logger.debug(
                f"Got error while trying to fetch {url}. {retries - i - 1} retries left.",
                exc_info=True,
            )
            exception = error
        else:
            return response
        sleep(backoff_factor)
    raise exception


def order_dict(data):
    """
    Order dict by default order
    """
    return OrderedDict(
        {
            k: order_dict(v) if isinstance(v, dict) else v
            for k, v in sorted(data.items())
        }
    )


def extract_none_deprecated_command_names_from_yml(yml_data: dict) -> list:
    """
    Go over all the commands in a yml file and return their names.
    Args:
        yml_data (dict): the yml content as a dict

    Returns:
        list: a list of all the commands names
    """
    commands_ls = []
    for command in yml_data.get("script", {}).get("commands", {}):
        if command.get("name") and not command.get("deprecated"):
            commands_ls.append(command.get("name"))
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
    for command in yml_data.get("script", {}).get("commands", {}):
        if command.get("deprecated"):
            commands_ls.append(command.get("name"))
    return commands_ls


def remove_copy_and_dev_suffixes_from_str(field_name: str) -> str:
    for _ in range(field_name.count("_")):
        for suffix in SUFFIX_TO_REMOVE:
            if field_name.endswith(suffix):
                field_name = field_name[: -len(suffix)]
    return field_name


def get_display_name(file_path: str | Path, file_data: dict | None = None) -> str:
    """Gets the entity display name from the file.

    :param file_path: The entity file path
    :param file_data: The entity file data

    :rtype: ``str``
    :return The display name
    """
    file_path = Path(file_path)

    if not file_data and file_path.suffix in (".yml", ".yaml", ".json"):
        file_data = get_file(file_path)

    if not file_data:
        file_data = {}

    if "display" in file_data:
        return file_data["display"]
    elif (
        "layout" in file_data
        and isinstance(file_data["layout"], dict)
        and "id" in file_data["layout"]
    ):
        return file_data["layout"]["id"]
    elif "name" in file_data:
        return file_data["name"]
    elif "TypeName" in file_data:
        return file_data["TypeName"]
    elif "brandName" in file_data:
        return file_data["brandName"]
    elif "details" in file_data and isinstance(file_data["details"], str):
        return file_data["details"]
    elif "id" in file_data:
        return file_data["id"]
    elif "trigger_name" in file_data:
        return file_data["trigger_name"]
    elif "rule_name" in file_data:
        return file_data["rule_name"]
    elif (
        "dashboards_data" in file_data
        and "dashboards_data" in file_data
        and isinstance(file_data["dashboards_data"], list)
        and len(file_data["dashboards_data"]) > 0
        and "name" in file_data["dashboards_data"][0]
    ):
        return file_data["dashboards_data"][0]["name"]
    elif (
        "templates_data" in file_data
        and "templates_data" in file_data
        and isinstance(file_data["templates_data"], list)
        and len(file_data["templates_data"]) > 0
        and "report_name" in file_data["templates_data"][0]
    ):
        return file_data["templates_data"][0]["report_name"]

    return file_path.name


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
    if mapping_type not in {"mapping-incoming", "mapping-outgoing"}:
        raise ValueError(
            f"Invalid mapping-type value {mapping_type}, should be: mapping-incoming/mapping-outgoing"
        )

    non_existent_fields = []

    for inc_name, inc_info in mapper_incident_fields.items():
        # incoming mapper
        if mapping_type == "mapping-incoming":
            if (
                inc_name not in content_fields
                and inc_name.lower() not in content_fields
            ):
                non_existent_fields.append(inc_name)
        # outgoing mapper
        if mapping_type == "mapping-outgoing":
            # for inc timer type: "field.StartDate, and for using filters: "simple": "".
            if simple := inc_info.get("simple"):
                if "." in simple:
                    simple = simple.split(".")[0]
                if (
                    simple not in content_fields
                    and simple.lower() not in content_fields
                ):
                    non_existent_fields.append(inc_name)

    return non_existent_fields


def get_invalid_incident_fields_from_layout(
    layout_incident_fields: List[Dict], content_fields: List[str]
) -> List[str]:
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
            inc_field_id = normalize_field_name(
                field=incident_field_info.get("fieldId", "")
            )
            if (
                inc_field_id
                and inc_field_id.lower() not in content_fields
                and inc_field_id not in content_fields
            ):
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
    return field.replace("incident_", "").replace("indicator_", "")


def string_to_bool(
    input_: Any,
    default_when_empty: Optional[bool] = None,
) -> bool:
    try:
        return STRING_TO_BOOL_MAP[str(input_).lower()]
    except (KeyError, TypeError):
        if input_ in ("", None) and default_when_empty is not None:
            return default_when_empty

    raise ValueError(f"cannot convert {input_} to bool")


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
    return re.sub(NON_LETTERS_OR_NUMBERS_PATTERN, "", field_name).lower()


def extract_field_from_mapping(mapping_value: str) -> str:
    """Given an outgoing-mapping value, returns the incident/indicator field used for the mapping.
    If mapping_value is surrounded by quotes ("<>"), it means the mapping value is a string and no field
    should be returned.

    Args:
        mapping_value (str): An outgoing-mapping value, which may contain an incident/indicator field.

    Returns:
        str: An incident/indicator field, or an empty string if not a field.
    """
    if not mapping_value or re.match(r"\"([^.]+).*\"", mapping_value):  # not a field
        return ""
    if field_name := re.match(r"\$\{([^.]*)[^}]*\}|([^$.]*).*", mapping_value):
        if field_name.groups()[0] is not None:
            return field_name.groups()[0]
        if len(field_name.groups()) > 1:
            return field_name.groups()[1]
    return mapping_value


def get_pack_paths_from_files(file_paths: Iterable[str]) -> list:
    """Returns the pack paths from a list/set of files"""
    pack_paths = {f"Packs/{get_pack_name(file_path)}" for file_path in file_paths}
    return list(pack_paths)


def replace_incident_to_alert(value: str) -> str:
    if not isinstance(value, str):
        return value

    new_value = value
    for pattern, replace_with in TABLE_INCIDENT_TO_ALERT.items():
        new_value = re.sub(pattern, replace_with, new_value)
    return new_value


def replace_alert_to_incident(value: str) -> str:
    if not isinstance(value, str):
        return value

    new_value = value
    for incident, alert in TABLE_INCIDENT_TO_ALERT.items():
        new_value = re.sub(alert, incident, new_value)
    return new_value


def get_id(file_content: Dict) -> Union[str, None]:
    """
    Get ID from a dict based content object.

    Args:
        file_content: the content of the file.

    Returns:
        str | None: the ID of the content item in case found, None otherwise.
    """
    if "commonfields" in file_content:
        return file_content["commonfields"].get("id")
    elif "dashboards_data" in file_content:
        return file_content["dashboards_data"][0].get("global_id")
    elif "templates_data" in file_content:
        return file_content["templates_data"][0].get("global_id")

    for key in (
        "global_rule_id",
        "trigger_id",
        "content_global_id",
        "rule_id",
        "typeId",
    ):
        if key in file_content:
            return file_content[key]

    return file_content.get("id")


def parse_marketplace_kwargs(kwargs: Dict[str, Any]) -> MarketplaceVersions:
    """
    Supports both the `marketplace` argument and `xsiam`.
    Raises an error when both are supplied.
    """
    marketplace = kwargs.pop("marketplace", None)  # removing to not pass it twice later
    is_xsiam = kwargs.get("xsiam")

    if (
        marketplace
        and is_xsiam
        and MarketplaceVersions(marketplace) != MarketplaceVersions.MarketplaceV2
    ):
        raise ValueError(
            "The arguments `marketplace` and `xsiam` cannot be used at the same time, remove one of them."
        )

    if is_xsiam:
        return MarketplaceVersions.MarketplaceV2

    if marketplace:
        return MarketplaceVersions(marketplace)

    logger.debug(
        "neither marketplace nor is_xsiam provided, using default marketplace=XSOAR"
    )
    return MarketplaceVersions.XSOAR  # default


def get_api_module_dependencies_from_graph(
    changed_api_modules: Set[str], graph: "ContentGraphInterface"
) -> List:
    if changed_api_modules:
        dependent_items = []
        api_module_nodes = graph.search(
            object_id=changed_api_modules, all_level_imports=True
        )
        if missing_api_modules := changed_api_modules - {
            node.object_id for node in api_module_nodes
        }:
            raise ValueError(
                f"The modified API modules {','.join(missing_api_modules)} were not found in the "
                f"content graph."
            )
        for api_module_node in api_module_nodes:
            logger.info(
                f"Checking for packages dependent on the modified API module {api_module_node.object_id}"
            )
            dependent_items += list(api_module_node.imported_by)

        if dependent_items:
            logger.info(
                f"Found [cyan]{len(dependent_items)}[/cyan] content items that import the following modified API modules: {changed_api_modules}. "
            )
        return dependent_items

    logger.info("No dependent packages found.")
    return []


def parse_multiple_path_inputs(
    input_path: Optional[Union[Path, str, List[Path], Tuple[Path]]]
) -> Optional[Tuple[Path, ...]]:
    if not input_path:
        return ()

    if isinstance(input_path, Path):
        return (input_path,)

    if isinstance(input_path, str):
        return tuple(Path(path_str) for path_str in input_path.split(","))

    if isinstance(input_path, (list, tuple)) and isinstance(
        (result := tuple(input_path))[0], Path
    ):
        return result

    raise ValueError(f"Cannot parse paths from {input_path}")


@lru_cache
def is_sdk_defined_working_offline() -> bool:
    """
    This method returns True when the SDK is defined as offline, i.e., when
    the DEMISTO_SDK_OFFLINE_ENV environment variable is True.

    Returns:
        bool: The value for DEMISTO_SDK_OFFLINE_ENV environment variable.
    """
    return str2bool(os.getenv(ENV_SDK_WORKING_OFFLINE))


def sha1_update_from_file(filename: Union[str, Path], hash):
    """This will iterate the file and update the hash object"""
    assert Path(filename).is_file()
    with open(str(filename), "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash


def sha1_file(filename: Union[str, Path]) -> str:
    """Return the sha1 hash of a directory"""
    return str(sha1_update_from_file(filename, sha1()).hexdigest())


def sha1_update_from_dir(directory: Union[str, Path], hash_):
    """This will recursivly iterate all the files in the directory and update the hash object"""
    assert Path(directory).is_dir()
    for path in sorted(Path(directory).iterdir(), key=lambda p: str(p).lower()):
        if path.name == "__pycache__":
            continue
        hash_.update(path.name.encode())
        if path.is_file():
            hash_ = sha1_update_from_file(path, hash_)
        elif path.is_dir():
            hash_ = sha1_update_from_dir(path, hash_)
    return hash_


def sha1_dir(directory: Union[str, Path]) -> str:
    """Return the sha1 hash of a directory"""
    return str(sha1_update_from_dir(directory, sha1()).hexdigest())


def is_epoch_datetime(string: str) -> bool:
    # Check if the input string contains only digits
    if not string.isdigit():
        return False
    # Convert the string to an integer and attempt to parse it as a datetime
    try:
        epoch_timestamp = int(string)
        datetime.fromtimestamp(epoch_timestamp)
        return True
    except Exception:
        return False


def extract_error_codes_from_file(pack_name: str) -> Set[str]:
    """
    Args:
        pack_name: a pack name from which to get the pack ignore errors.
    Returns: error codes set  that in pack.ignore file
    """
    error_codes_list = []
    if pack_name and (config := get_pack_ignore_content(pack_name)):
        # go over every file in the config
        for section in filter(
            lambda section: section.startswith("file:"), config.sections()
        ):
            # given section is of type file
            for key in config[section]:
                if key == "ignore":
                    # group ignore codes to a list
                    error_codes = str(config[section][key]).split(",")
                    error_codes_list.extend(error_codes)

    return set(error_codes_list)


def is_string_ends_with_url(str: str) -> bool:
    """
    Args:
        str: a string to test.
    Returns: True if the string ends with a url adress. Otherwise, return False.
    """
    return bool(re.search(f"{URL_REGEX}$", str))


def strip_description(description):
    """
    Args:
        description: a description string.
    Returns: the description stripped from quotes mark if they appear both in the beggining and in the end of the string.
    """
    description = description.strip()
    return (
        description.strip('"')
        if description.startswith('"') and description.endswith('"')
        else description.strip("'")
        if description.startswith("'") and description.endswith("'")
        else description
    )


def is_file_in_pack(file: Path, pack_name: str) -> bool:
    """
    Return wether the given file is under the given pack.
    Args:
        file: The file to check.
        pack_name: The name of the pack we want to ensure the given file is under.
    """
    return (
        len(file.parts) > 2 and file.parts[0] == "Packs" and file.parts[1] == pack_name
    )


def parse_int_or_default(value: Any, default: int) -> int:
    """
    Parse int or return default value
    Args:
        value: value to parse
        default: default value to return if parsing failed

    Returns:
        int: parsed value or default value

    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_all_repo_pack_ids() -> list:
    return [path.name for path in (Path(get_content_path()) / PACKS_DIR).iterdir()]


def get_value(obj: dict, paths: Union[str, List[str]], defaultParam=None):
    """Extracts field value from nested object
    Args:
      obj (dict): The object to extract the field from
      field (Union[str,List[str]]): The field or a list of possible fields to extract from the object, given in dot notation
      defaultParam (object): The default value to return in case the field doesn't exist in obj
    Returns:
      str: The value of the extracted field
    """
    if isinstance(paths, str):
        paths = [paths]
    for path in paths:
        keys = path.split(".")
        temp_obj = obj
        success = True
        for key in keys:
            try:
                if "[" in key and "]" in key:
                    # Handle list indexing
                    list_key, index = key.split("[")
                    index = int(index.strip("]"))  # type: ignore
                    temp_obj = temp_obj[list_key][index]
                else:
                    temp_obj = temp_obj[key]
            except (AttributeError, KeyError, IndexError):
                success = False
                continue
        if success:
            return temp_obj
    return defaultParam


def find_correct_key(data: dict, keys: List[str]) -> str:
    """Given a data object and a list of possible paths, finding the path where the object holds a value in that path.
    Args:
        data (dict): The object that holds the keys.
        keys (List[str]) List of possible paths.
    Returns:
        str: Either the path where the given data object has a value at or the last option.
    """
    for key in keys:
        if get_value(data, key, None):
            return key
    return keys[-1]


def set_value(data: dict, paths: Union[str, List[str]], value) -> None:
    """Updating a data object with given value in the given key.
    If a list of keys is given, will find the right path to update based on which path acctually has a value.
    Args:
        data (dict): the data object to update.
        keys (Union[str,List[str]]): the path or list of possible paths to update.
        value (_type_): the value to update.
    """
    if isinstance(paths, list):
        path = find_correct_key(data, paths)
    else:
        path = paths
    current_dict = data
    keys = path.split(".")
    for key in keys[:-1]:
        if "[" in key and "]" in key:
            # Handle list indexing
            list_key, index = key.split("[")
            index = int(index.strip("]"))
            current_dict = current_dict[list_key]
            current_dict = current_dict[index]
        else:
            # Handle dictionary keys
            current_dict = current_dict[key]

    # Set the value in the dictionary at the specified path
    last_key = keys[-1]
    if "[" in last_key and "]" in last_key:
        list_key, index = last_key.split("[")  # type: ignore
        index = int(index.strip("]"))  # type: ignore
        current_dict[list_key][index] = value
    else:
        current_dict[last_key] = value


def detect_file_level(file_path: str) -> PathLevel:
    """
    Detect the whether the path points to a file, a content entity dir, a content generic entity dir
    (i.e GenericFields or GenericTypes), a pack dir or package dir

    Args:
            file_path(str): the path to check.

    Returns:
        PathLevel. File, ContentDir, ContentGenericDir, Pack or Package - depending on the file path level.
    """
    if Path(file_path).is_file():
        return PathLevel.FILE

    file_path = file_path.rstrip("/")
    dir_name = Path(file_path).name
    if dir_name in CONTENT_ENTITIES_DIRS:
        return PathLevel.CONTENT_ENTITY_DIR

    if str(os.path.dirname(file_path)).endswith(GENERIC_TYPES_DIR) or str(
        os.path.dirname(file_path)
    ).endswith(GENERIC_FIELDS_DIR):
        return PathLevel.CONTENT_GENERIC_ENTITY_DIR

    if Path(file_path).parent.name == PACKS_DIR:
        return PathLevel.PACK

    else:
        return PathLevel.PACKAGE


def specify_files_from_directory(file_set: Set, directory_path: str) -> Set:
    """Filter a set of file paths to only include ones which are from a specified directory.

    Args:
        file_set(Set): A set of file paths - could be stings or tuples for rename files.
        directory_path(str): the directory path in which to check for the files.

    Returns:
        Set. A set of all the paths of files that appear in the given directory.
    """
    filtered_set: Set = set()
    for file in file_set:
        if isinstance(file, str) and directory_path in file:
            filtered_set.add(file)

        # handle renamed files
        elif isinstance(file, tuple) and directory_path in file[1]:
            filtered_set.add(file)

    return filtered_set


def get_file_by_status(
    modified_files: Set,
    old_format_files: Optional[Set],
    file_path: str,
    renamed_files: Optional[Set] = None,
) -> Tuple[Set, Set, Set]:
    """Given a specific file path identify in which git status set
    it exists and return a set containing that file and 2 additional empty sets.

    Args:
        modified_files(Set): A set of modified and renamed files.
        old_format_files(Optional[Set]): A set of old format files.
        file_path(str): The file path to check.
        renamed_files(Optional[Set]): A set of renamed files.

    Returns:
        Tuple[Set, Set, Set]. 3 sets representing modified, added and old format or renamed files respectively
        where the file path is in the appropriate set
    """
    filtered_modified_files: Set = set()
    filtered_added_files: Set = set()
    filtered_old_format_or_renamed_files: Set = set()

    # go through modified files and try to identify if the file is there
    for file in modified_files:
        if isinstance(file, str) and file == file_path:
            filtered_modified_files.add(file_path)
            return (
                filtered_modified_files,
                filtered_added_files,
                filtered_old_format_or_renamed_files,
            )

        # handle renamed files which are in tuples
        elif file_path in file:
            filtered_modified_files.add(file)
            return (
                filtered_modified_files,
                filtered_added_files,
                filtered_old_format_or_renamed_files,
            )
    if renamed_files:
        for file in renamed_files:
            if file_path in file:
                filtered_old_format_or_renamed_files.add(file)
                return (
                    filtered_modified_files,
                    filtered_added_files,
                    filtered_old_format_or_renamed_files,
                )

    # if the file is not modified check if it is in old format files
    if old_format_files and file_path in old_format_files:
        filtered_old_format_or_renamed_files.add(file_path)

    else:
        # if not found in either modified or old format consider the file newly added
        filtered_added_files.add(file_path)

    return (
        filtered_modified_files,
        filtered_added_files,
        filtered_old_format_or_renamed_files,
    )


def pascal_to_snake(pascal_string):
    """Convert the given string from pascal case to snake case.

    Args:
        pascal_string(str): A string in pascal case format

    Returns:
        str: The givn string converted to snake_case format.
    """
    result = [pascal_string[0].lower()]
    for char in pascal_string[1:]:
        if char.isupper():
            result.extend(["_", char.lower()])
        else:
            result.append(char)
    return "".join(result)


def retry(
    times: int = 3,
    delay: int = 1,
    exceptions: Union[Tuple[Type[Exception], ...], Type[Exception]] = Exception,
):
    """
    retries to execute a function until an exception isn't raised anymore.

    Args:
        times: the amount of times to try and execute the function
        delay: the number of seconds to wait between each time
        exceptions: the exceptions that should be caught when executing the function

    Returns:
        Any: the decorated function result
    """

    def _retry(func: Callable):
        func_name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(1, times + 1):
                logger.debug(f"trying to run func {func_name} for the {i} time")
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    logger.debug(
                        f"error when executing func {func_name}, error: {error}, time {i}"
                    )
                    if i == times:
                        raise
                    time.sleep(delay)

        return wrapper

    return _retry


def is_abstract_class(cls):
    return ABC in getattr(cls, "__bases__", ())


class SecretManagerException(Exception):
    pass


def get_integration_params(secret_id: str, project_id: Optional[str] = None) -> dict:
    """This function retrieves the parameters of an integration from Google Secret Manager
    *Note*: This function will not run if the `DEMISTO_SDK_GCP_PROJECT_ID` env variable is not set.

    Args:
        project_id (str): GSM project id
        secret_id (str): The secret id in GSM

    Returns:
        dict: The integration params
    """
    if not project_id:
        project_id = os.getenv("DEMISTO_SDK_GCP_PROJECT_ID")
    if not project_id:
        raise ValueError(
            "Either provide the project id or set the `DEMISTO_SDK_GCP_PROJECT_ID` environment variable"
        )

    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    # Access the secret version.
    try:
        response = client.access_secret_version(name=name)
    except google.api_core.exceptions.NotFound:
        logger.warning("The secret is not found in the secret manager")
        raise SecretManagerException
    except (
        google.api_core.exceptions.PermissionDenied,
        google.auth.exceptions.DefaultCredentialsError,
    ):
        logger.warning(
            "Insufficient permissions for gcloud. run `gcloud auth application-default login`"
        )
        raise SecretManagerException
    except Exception:
        logger.warning(f"Failed to get secret {secret_id} from Secret Manager.")
        raise SecretManagerException
    # Return the decoded payload.
    payload = json5.loads(response.payload.data.decode("UTF-8"))
    if "params" not in payload:
        logger.warning(f"Parameters are not found in {secret_id} from Secret Manager.")

        raise SecretManagerException
    return payload["params"]


def check_timestamp_format(timestamp: str) -> bool:
    """Check that the timestamp is in ISO format"""
    try:
        datetime.strptime(timestamp, ISO_TIMESTAMP_FORMAT)
        return True
    except ValueError:
        return False


def get_pack_latest_rn_version(pack_path: str) -> str:
    """
    Extract all the Release notes from the pack and return the highest version of release note in the Pack.

    Return:
        (str): The lastest version of RN.
    """
    list_of_files = glob.glob(pack_path + "/ReleaseNotes/*")
    list_of_release_notes = [Path(file).name for file in list_of_files]
    list_of_versions = [
        rn[: rn.rindex(".")].replace("_", ".") for rn in list_of_release_notes
    ]
    if list_of_versions:
        list_of_versions.sort(key=Version)
        return list_of_versions[-1]
    else:
        return ""


def is_str_bool(input_: str) -> bool:
    try:
        string_to_bool(input_)
        return True
    except ValueError:
        return False


def check_text_content_contain_sub_text(
    sub_text_list: List[str],
    is_lower: bool = False,
    to_split: bool = False,
    text: str = "",
) -> List[str]:
    """
    Args:
        sub_text_list (List[str]): list of words/sentences to search in line content.
        is_lower (bool): True to check when line is lower cased.
        to_split (bool): True to split the line in order to search specific word
        text (str): The readme content to search.

    Returns:
        list of lines which contains the given text.
    """
    invalid_lines = []

    for line_num, line in enumerate(text.split("\n")):
        if is_lower:
            line = line.lower()
        if to_split:
            line = line.split()  # type: ignore
        for text in sub_text_list:
            if text in line:
                invalid_lines.append(str(line_num + 1))

    return invalid_lines


def extract_image_paths_from_str(
    text: str, regex_str: str = r"!\[.*\]\((.*/doc_files/[a-zA-Z0-9_-]+\.png)"
) -> List[str]:
    """
    Args:
        local_paths (List[str]): list of file paths
        is_lower (bool): True to check when line is lower cased.
        to_split (bool): True to split the line in order to search specific word
        text (str): The readme content to search.

    Returns:
        list of lines which contains the given text.
    """

    return [image_path for image_path in re.findall(regex_str, text)]


def get_full_image_paths_from_relative(
    pack_name: str, image_paths: List[str]
) -> List[Path]:
    """
        Args:
            pack_name (str): Pack name to add to path
            image_paths (List[Path]): List of images with a local path. For example: ![<title>](../doc_files/<image name>.png)
    )

        Returns:
            List[Path]: A list of paths with the full path.
    """

    return [
        Path(f"Packs/{pack_name}/{image_path.replace('../', '')}")
        if "Packs" not in image_path
        else Path(image_path)
        for image_path in image_paths
    ]


def remove_nulls_from_dictionary(data):
    """
    Remove Null values from a dictionary. (updating the given dictionary)

    :type data: ``dict``
    :param data: The data to be added to the context (required)

    :return: No data returned
    :rtype: ``None``
    """
    list_of_keys = list(data.keys())[:]
    for key in list_of_keys:
        if data[key] in ("", None, [], {}, ()):
            del data[key]

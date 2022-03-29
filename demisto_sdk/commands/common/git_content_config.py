"""
This is module to store the git configuration of the content repo
"""
import enum
import os
from functools import lru_cache
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import click
import giturlparse
# dirs
import requests
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger

json = JSON_Handler()


class GitProvider(enum.Enum):
    GitHub = 'github'
    GitLab = 'gitlab'


class GitCredentials:
    ENV_GITHUB_TOKEN_NAME = 'DEMISTO_SDK_GITHUB_TOKEN'
    ENV_GITLAB_TOKEN_NAME = 'DEMISTO_SDK_GITLAB_TOKEN'

    def __init__(self):
        self.github_token = os.getenv(self.ENV_GITHUB_TOKEN_NAME)
        self.gitlab_token = os.getenv(self.ENV_GITLAB_TOKEN_NAME)


class GitContentConfig:
    """Holds links, credentials and other content related github configuration

    Attributes:
        credentials: Credentials to the git.
    """
    BASE_RAW_GITHUB_LINK = r'https://raw.{GITHUB_HOST}/'
    SDK_API_GITHUB_RELEASES = r'https://api.github.com/repos/demisto/demisto-sdk/releases'
    OFFICIAL_CONTENT_REPO_NAME = 'demisto/content'
    CONTENT_GITHUB_UPSTREAM = r'upstream.*demisto/content'
    CONTENT_GITHUB_ORIGIN = r'origin.*demisto/content'
    GITHUB_USER_CONTENT = 'githubusercontent.com'

    BASE_RAW_GITLAB_LINK = "https://{GITLAB_HOST}/api/v4/projects/{GITLAB_ID}/repository"

    ENV_REPO_HOSTNAME_NAME = 'DEMISTO_SDK_REPO_HOSTNAME'

    def __init__(
            self,
            repo_name: Optional[str] = None,
            git_provider: Optional[GitProvider] = GitProvider.GitHub,
            repo_hostname: Optional[str] = None,
            project_id: Optional[int] = None
    ):
        """
        Args:
            repo_name: Name of the repo (e.g "demisto/content")
            git_provider: The git provider to use (e.g GitProvider.GitHub, GitProvider.GitLab)
            repo_hostname: The hostname to use (e.g "code.pan.run", "gitlab.com", "my-hostename.com")
            project_id: The project id, relevant for gitlab.
        """
        self.current_repository = repo_name if repo_name else None
        if project_id:
            git_provider = GitProvider.GitLab

        self.credentials = GitCredentials()
        hostname = urlparse(repo_hostname).hostname
        self.repo_hostname = hostname or repo_hostname or os.getenv(GitContentConfig.ENV_REPO_HOSTNAME_NAME)
        self.git_provider = git_provider
        if not self.repo_hostname:
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT if git_provider == GitProvider.GitHub else "gitlab.com"
        if self.repo_hostname == 'github.com':
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT

        parsed_git = GitContentConfig._get_repository_properties()

        if parsed_git is None:
            hostname = self.repo_hostname
            organization = None
            repo_name = self.current_repository
        else:
            hostname = parsed_git.host
            organization = parsed_git.owner
            repo_name = parsed_git.repo
            if '@' in parsed_git.host:  # the library sometimes returns hostname as <username>@<hostname>
                hostname = parsed_git.host.split('@')[1]  # to get proper hostname, without the username or tokens

        self._set_repo_config(hostname, organization, repo_name, project_id)

        if self.git_provider == GitProvider.GitHub:
            # DO NOT USE os.path.join on URLs, it may cause errors
            self.base_api = urljoin(GitContentConfig.BASE_RAW_GITHUB_LINK.format(GITHUB_HOST=self.repo_hostname),
                                    self.current_repository)
        else:  # gitlab
            self.base_api = GitContentConfig.BASE_RAW_GITLAB_LINK.format(GITLAB_HOST=self.repo_hostname,
                                                                         GITLAB_ID=self.gitlab_id)

    @staticmethod
    def _get_repository_properties() -> Optional[giturlparse.result.GitUrlParsed]:
        """Returns the git repository of the cwd.
        if not running in a git repository, will return an empty string
        """
        try:
            urls = GitUtil().repo.remote().urls
            for url in urls:
                parsed_git = giturlparse.parse(url)
                if parsed_git and parsed_git.host and parsed_git.repo:
                    return parsed_git
        except (InvalidGitRepositoryError, AttributeError):
            return None
        return None

    def _set_repo_config(self, hostname, organization=None, repo_name=None, project_id=None):

        gitlab_hostname, gitlab_id = (self._search_gitlab_repo(hostname, project_id=project_id)) or \
                                     (self._search_gitlab_repo(self.repo_hostname, project_id=project_id)) or \
                                     (self._search_gitlab_repo(hostname, repo_name=repo_name)) or \
                                     (self._search_gitlab_repo(self.repo_hostname, repo_name=repo_name)) or \
                                     (None, None)

        if self.git_provider == GitProvider.GitLab and gitlab_id is None:
            click.secho(f'If your repo is in private gitlab repo, '
                        f'configure `{GitCredentials.ENV_GITLAB_TOKEN_NAME}` environment variable '
                        f'or configure `{GitContentConfig.ENV_REPO_HOSTNAME_NAME}` environment variable', fg='yellow')
            click.secho('Could not find the repository name on gitlab - defaulting to demisto/content', fg='yellow')
            self.git_provider = GitProvider.GitHub
            self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT
            return

        if gitlab_id is not None:
            self.git_provider = GitProvider.GitLab
            self.gitlab_id: int = gitlab_id
            self.repo_hostname = gitlab_hostname
        else:  # github
            current_repo = f'{organization}/{repo_name}' if organization and repo_name else self.current_repository
            github_hostname, github_repo = self._search_github_repo(hostname, self.current_repository) or \
                self._search_github_repo(self.repo_hostname, current_repo) \
                or (None, None)
            self.git_provider = GitProvider.GitHub
            if not github_hostname or not github_repo:  # github was not found.
                click.secho(f'If your repo is in private github repo, '
                            f'configure `{GitCredentials.ENV_GITLAB_TOKEN_NAME}` environment variable '
                            f'or configure `{GitContentConfig.ENV_REPO_HOSTNAME_NAME}` environment variable',
                            fg='yellow')
                click.secho('Could not find the repository name on gitlab - defaulting to demisto/content', fg='yellow')
                self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
                self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT
            else:
                self.repo_hostname = github_hostname
                self.current_repository = github_repo

    @lru_cache(maxsize=128)
    def _search_github_repo(self, github_hostname, repo_name) -> Optional[Tuple[str, str]]:
        """
        Searches the github API for the repo
        Args:
            github_hostname: hostname of github.
            repo_name: repository name in this structure: "<org_name>/<repo_name>".

        Returns:
            If found -  a tuple of the github hostname and the repo name that was found.
            If not found - 'None`
        """
        if not github_hostname or not repo_name:
            return None
        api_host = github_hostname if github_hostname != GitContentConfig.GITHUB_USER_CONTENT else 'github.com'
        if api_host.lower() == 'github.com':
            github_hostname = GitContentConfig.GITHUB_USER_CONTENT
        try:
            r = requests.get(f'https://api.{api_host}/repos/{repo_name}',
                             headers={
                                 'Authorization': f"Bearer {self.credentials.github_token}" if self.credentials.github_token else None,
                                 'Accept': 'application/vnd.github.VERSION.raw'},
                             verify=False,
                             timeout=10)
            if r.ok:
                return github_hostname, repo_name
            r = requests.get(f'https://api.{api_host}/repos/{repo_name}',
                             verify=False,
                             params={'token': self.credentials.github_token},
                             timeout=10)
            if r.ok:
                return github_hostname, repo_name
            logger.debug('Could not access GitHub api in `_search_github_repo`')
            return None
        except requests.exceptions.ConnectionError as e:
            logger.debug(str(e), exc_info=True)
            return None

    @lru_cache(maxsize=128)
    def _search_gitlab_repo(self, gitlab_hostname: str, repo_name: Optional[str] = None,
                            project_id: Optional[int] = None) -> \
            Optional[Tuple[str, int]]:
        """
        Searches the gitlab API for the repo.
        One of `repo_name` or `project_id` is mandatory.
        Args:
            gitlab_hostname: hostname of gitlab.
            repo_name: The repo name to search.
            project_id: The project id to search

        Returns:
            If found - A tuple of the gitlab hostname and the gitlab id.
            If not found - `None`.

        """
        if not gitlab_hostname or \
                gitlab_hostname == GitContentConfig.GITHUB_USER_CONTENT or \
                gitlab_hostname == 'github.com':
            return None
        try:
            if project_id:
                res = requests.get(f"https://{gitlab_hostname}/api/v4/projects/{project_id}",
                                   headers={'PRIVATE-TOKEN': self.credentials.gitlab_token},
                                   timeout=10,
                                   verify=False)
                if res.ok:
                    return gitlab_hostname, project_id

            if repo_name:
                res = requests.get(f"https://{gitlab_hostname}/api/v4/projects",
                                   params={'search': repo_name},
                                   headers={'PRIVATE-TOKEN': self.credentials.gitlab_token},
                                   timeout=10,
                                   verify=False)
                if not res.ok:
                    return None
                search_results = res.json()
                assert search_results and isinstance(search_results, list) and isinstance(search_results[0], dict)
                gitlab_id = search_results[0].get('id')
                if gitlab_id is None:
                    return None
                return gitlab_hostname, gitlab_id
            logger.debug('Could not access GitLab api in `_search_gitlab_repo`')
            return None

        except (requests.exceptions.ConnectionError, json.JSONDecodeError, AssertionError) as e:
            logger.debug(str(e), exc_info=True)
            return None

"""
This is module to store the git configuration of the content repo
"""
import enum
import json
import logging
import os
from functools import lru_cache
from typing import Optional, Tuple
from urllib.parse import urljoin

import click
import giturlparse
# dirs
import requests
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.git_util import GitUtil


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

    def __init__(self, repo_name: Optional[str] = None, git_provider: Optional[GitProvider] = GitProvider.GitHub, repo_hostname: Optional[str] = None):
        self.credentials = GitCredentials()
        self.repo_hostname = repo_hostname or os.getenv(GitContentConfig.ENV_REPO_HOSTNAME_NAME)
        self.git_provider = git_provider
        if not self.repo_hostname:
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT if git_provider == GitProvider.GitHub else "gitlab.com"

        if 'github.com' in self.repo_hostname:
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT

        if 'gitlab.com' in self.repo_hostname:
            self.repo_hostname = 'gitlab.com'

        if not repo_name:  # repo_name is not specified, parsing the remote url the get the details
            try:
                parsed_git = GitContentConfig._get_repository_properties()
                self._set_repo_config(parsed_git)
            except (InvalidGitRepositoryError, AttributeError):  # No repository
                click.secho('No repository was found - defaulting to demisto/content', fg='yellow')
                self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        else:
            self.current_repository = repo_name
            repo_hostname, gitlab_id = self._search_gitlab_id(self.repo_hostname, repo_name) or (None, None)
            if gitlab_id:
                self.gitlab_id = gitlab_id
            else:
                if self.git_provider == GitProvider.GitLab:
                    click.secho(f'If your repo is in private gitlab repo, '
                                f'configure `{GitCredentials.ENV_GITLAB_TOKEN_NAME}` environment variable '
                                f'or configure `{GitContentConfig.ENV_REPO_HOSTNAME_NAME}` environment variable',
                                fg='yellow')
                    click.secho('Could not find the repository name on gitlab - defaulting to demisto/content', fg='yellow')
                self.git_provider = GitProvider.GitHub
                self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
                self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT

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
        urls = GitUtil().repo.remote().urls
        for url in urls:
            parsed_git = giturlparse.parse(url)
            if parsed_git and parsed_git.host and parsed_git.repo:
                return parsed_git
        return None

    def _set_repo_config(self, parsed_git: Optional[giturlparse.result.GitUrlParsed]):
        if parsed_git is None:
            # default to content repo if the repo is not found
            click.secho('Could not find the repository name - defaulting to demisto/content', fg='yellow')
            self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT
            return
        hostname = parsed_git.host
        if '@' in hostname:  # the library sometimes returns hostname as <username>@<hostname>
            hostname = hostname.split('@')[1]  # to get proper hostname, without the username or tokens
        gitlab_hostname, gitlab_id = (self._search_gitlab_id(hostname, parsed_git.repo)) or \
                                     (self._search_gitlab_id(self.repo_hostname, parsed_git.repo)) or \
                                     (None, None)

        if self.git_provider == GitProvider.GitLab and not gitlab_id:
            click.secho(f'If your repo is in private gitlab repo, '
                        f'configure `{GitCredentials.ENV_GITLAB_TOKEN_NAME}` environment variable '
                        f'or configure `{GitContentConfig.ENV_REPO_HOSTNAME_NAME}` environment variable', fg='yellow')
            click.secho('Could not find the repository name on gitlab - defaulting to demisto/content', fg='yellow')
            self.git_provider = GitProvider.GitHub
            self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT
            return

        if gitlab_id:
            self.git_provider = GitProvider.GitLab
            self.gitlab_id = gitlab_id
            self.repo_hostname = gitlab_hostname
        else:  # github
            if self.repo_hostname == GitContentConfig.GITHUB_USER_CONTENT and 'github.com' not in hostname:
                click.secho(f'Found custom github url - defaulting to demisto/content. '
                            f'Configure `{GitContentConfig.ENV_REPO_HOSTNAME_NAME}` or `repo_hostname` argument'
                            f' to the repository address. '
                            f'defaulting to demisto/content', fg='yellow')
                self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            else:
                self.current_repository = f'{parsed_git.owner}/{parsed_git.repo}'

    @lru_cache(maxsize=10)
    def _search_gitlab_id(self, gitlab_hostname: str, repo: str) -> Optional[Tuple[Optional[str], Optional[int]]]:
        if not gitlab_hostname or gitlab_hostname == GitContentConfig.GITHUB_USER_CONTENT or 'github.com' in gitlab_hostname:
            return None
        try:
            res = requests.get(f"https://{gitlab_hostname}/api/v4/projects",
                               params={'search': repo},
                               headers={'PRIVATE-TOKEN': self.credentials.gitlab_token},
                               timeout=10,
                               verify=False)
            if not res.ok:
                return None
            search_results = res.json()
            assert search_results and isinstance(search_results, list) and isinstance(search_results[0], dict)
            gitlab_id = search_results[0].get('id')
            if not gitlab_id:
                return None
            return gitlab_hostname, gitlab_id
        except (requests.exceptions.ConnectionError, json.JSONDecodeError, AssertionError) as e:
            logging.getLogger('demisto-sdk').debug(str(e), exc_info=True)
            return None

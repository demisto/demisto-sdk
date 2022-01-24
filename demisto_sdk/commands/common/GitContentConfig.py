import os
from functools import lru_cache
from typing import Iterable, Optional, Tuple
from urllib.parse import urljoin

import click
import giturlparse
# dirs
import requests
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.git_util import GitUtil


class GitCredentials:
    ENV_GITHUB_TOKEN_NAME = 'DEMISTO_SDK_GITHUB_TOKEN'
    ENV_GITLAB_TOKEN_NAME = 'DEMISTO_SDK_GITLAB_TOKEN'

    def __init__(self):
        self.github_token = os.getenv(self.ENV_GITHUB_TOKEN_NAME)
        self.gitlab_token = os.getenv(self.ENV_GITLAB_TOKEN_NAME)


class GitContentConfig:
    """Holds links, credentials and other content related github configuration

    Attributes:
        Credentials: Credentials to the git.
    """
    BASE_RAW_GITHUB_LINK = r'https://raw.{GITHUB_HOST}/'
    SDK_API_GITHUB_RELEASES = r'https://api.github.com/repos/demisto/demisto-sdk/releases'
    OFFICIAL_CONTENT_REPO_NAME = 'demisto/content'
    CONTENT_GITHUB_UPSTREAM = r'upstream.*demisto/content'
    CONTENT_GITHUB_ORIGIN = r'origin.*demisto/content'

    BASE_RAW_GITLAB_LINK = "https://{GITLAB_HOST}/api/v4/projects/{GITLAB_ID}/repository"

    ENV_IS_GITLAB_NAME = 'DEMISTO_SDK_IS_GITLAB'
    ENV_REPO_URL_NAME = 'DEMISTO_SDK_REPO_URL'

    def __init__(self, repo_name: Optional[str] = None):
        self.Credentials = GitCredentials()
        self.is_gitlab = bool(os.getenv(GitContentConfig.ENV_IS_GITLAB_NAME, False))
        self.base_repo_url = os.getenv(GitContentConfig.ENV_REPO_URL_NAME)

        if not repo_name:
            try:
                urls = list(GitUtil().repo.remote().urls)
                parsed_git = self._get_repository_properties(urls)
                self._set_repo_config(parsed_git)
            except (InvalidGitRepositoryError, AttributeError):  # No repository
                self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        else:
            self.current_repository = repo_name
        if not self.is_gitlab:
            # DO NOT USE os.path.join on URLs, it may cause errors
            self.base_api = urljoin(GitContentConfig.BASE_RAW_GITHUB_LINK.format(GITHUB_HOST=self.base_repo_url),
                                    self.current_repository)
        else:
            self.base_api = GitContentConfig.BASE_RAW_GITLAB_LINK.format(GITLAB_HOST=self.base_repo_url,
                                                                         GITLAB_ID=self.gitlab_id)

    @staticmethod
    def _get_repository_properties(urls: Iterable) -> Optional[giturlparse.result.GitUrlParsed]:
        """Returns the git repository of the cwd.
        if not running in a git repository, will return an empty string
        """
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
            return
        hostname = parsed_git.host
        if '@' in hostname:
            hostname = hostname.split('@')[1]  # to get proper hostname, without the username or tokens
        gitlab_hostname, gitlab_id = (self._search_gitlab_id(hostname, parsed_git.repo)) or \
                                     (self._search_gitlab_id(self.base_repo_url, parsed_git.repo)) or \
                                     (None, None)

        if self.is_gitlab and not gitlab_id:
            click.secho(f'If your repo is in private gitlab repo, '
                        f'configure `{GitCredentials.ENV_GITLAB_TOKEN_NAME}` environment variable '
                        f'or configure `{GitContentConfig.ENV_REPO_URL_NAME}` environment variable', fg='yellow')
            click.secho('Could not find the repository name on gitlab - defaulting to demisto/content', fg='yellow')
            self.is_gitlab = False
            self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            self.base_repo_url = 'githubusercontent.com'
            return

        if gitlab_id:
            self.is_gitlab = True
            self.gitlab_id: int = gitlab_id
            self.base_repo_url = gitlab_hostname
        else:  # github
            if not self.base_repo_url:  # if the env variable not configured, check if this is a custom hostname or not
                if 'github.com' not in hostname:
                    click.secho(f'Found custom github url - defaulting to demisto/content. '
                                f'Configure `{GitContentConfig.ENV_REPO_URL_NAME}` to the repository address', fg='yellow')
                    self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
                else:
                    self.current_repository = f'{parsed_git.owner}/{parsed_git.repo}'
                self.base_repo_url = 'githubusercontent.com'
            elif 'github.com' in self.base_repo_url.lower():
                self.current_repository = f'{parsed_git.owner}/{parsed_git.repo}'
                self.base_repo_url = 'githubusercontent.com'
            else:
                self.current_repository = f'{parsed_git.owner}/{parsed_git.repo}'

    @lru_cache(maxsize=10)
    def _search_gitlab_id(self, gitlab_hostname: str, repo: str) -> Optional[Tuple[Optional[str], Optional[int]]]:
        try:
            res = requests.get(f"https://{gitlab_hostname}/api/v4/projects",
                               params={'search': repo},
                               headers={'PRIVATE-TOKEN': self.Credentials.gitlab_token},
                               timeout=10,
                               verify=False)
            if not res.ok:
                return None
            search_results = res.json()
            gitlab_id = search_results[0].get('id', None) if search_results else None
            if not gitlab_id:
                return None
            return gitlab_hostname, gitlab_id
        except Exception:
            return None

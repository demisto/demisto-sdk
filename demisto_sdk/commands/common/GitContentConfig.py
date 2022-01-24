import os
from functools import lru_cache
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import click
import giturlparse
# dirs
import requests
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.git_util import GitUtil


class GitCredentials:
    ENV_GITHUB_TOKEN_NAME = 'DEMISTO_SDK_GITHUB_TOKEN'
    ENV_GITLAB_TOKEN_NAME = 'DEMISTO_SDK_GITLAB_TOKEN'
    GITHUB_TOKEN: Optional[str]
    GITLAB_TOKEN: Optional[str]

    def __init__(self):
        self.GITHUB_TOKEN = os.getenv(self.ENV_GITHUB_TOKEN_NAME)
        self.GITLAB_TOKEN = os.getenv(self.ENV_GITLAB_TOKEN_NAME)


class GitContentConfig:
    """Holds links, credentials and other content related github configuration

    Attributes:
        CURRENT_REPOSITORY: The current repository in the cwd
        CONTENT_GITHUB_LINK: Link to the raw content git repository
        CONTENT_GITHUB_MASTER_LINK: Link to the content git repository's master branch
        Credentials: Credentials to the git.
    """
    BASE_RAW_GITHUB_LINK = r'https://raw.{}.com/'
    SDK_API_GITHUB_RELEASES = r'https://api.github.com/repos/demisto/demisto-sdk/releases'
    OFFICIAL_CONTENT_REPO_NAME = 'demisto/content'
    CONTENT_GITHUB_UPSTREAM = r'upstream.*demisto/content'
    CONTENT_GITHUB_ORIGIN = r'origin.*demisto/content'

    CURRENT_REPOSITORY: str
    CONTENT_GITHUB_LINK: str
    CONTENT_GITHUB_MASTER_LINK: str

    BASE_RAW_GITLAB_LINK = "https://{GITLAB_HOST}/api/v4/projects/{GITLAB_ID}/repository"

    ENV_IS_GITLAB_NAME = 'DEMISTO_SDK_IS_GITLAB'
    ENV_REPO_URL_NAME = 'DEMISTO_SDK_REPO_URL'

    def __init__(self, repo_name: Optional[str] = None):
        self.Credentials = GitCredentials()
        self.is_gitlab = os.getenv(GitContentConfig.ENV_IS_GITLAB_NAME, False)
        self.base_url = os.getenv(GitContentConfig.ENV_REPO_URL_NAME)

        if not repo_name:
            try:
                urls = list(GitUtil().repo.remote().urls)
                parsed_git = self._get_repository_properties(urls)
                self._set_repo_config(parsed_git)
            except (InvalidGitRepositoryError, AttributeError):  # No repository
                self.CURRENT_REPOSITORY = self.OFFICIAL_CONTENT_REPO_NAME
        else:
            self.CURRENT_REPOSITORY = repo_name
        if not self.is_gitlab:
            # DO NOT USE os.path.join on URLs, it may cause errors
            self.CONTENT_GITHUB_LINK = urljoin(self.BASE_RAW_GITHUB_LINK.format(self.base_url), self.CURRENT_REPOSITORY)
            self.CONTENT_GITHUB_MASTER_LINK = urljoin(self.CONTENT_GITHUB_LINK, r'master')

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
            self.CURRENT_REPOSITORY = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            return
        hostname = urlparse(parsed_git.url).hostname
        gitlab_id = self._search_gitlab_id(hostname, parsed_git.repo) or self._search_gitlab_id(self.base_url,
                                                                                                parsed_git.repo)

        if self.is_gitlab and not gitlab_id:
            click.secho('If your repo is in private gitlab repo,'
                        ' configure `DEMISTO_SDK_GITLAB_TOKEN` environment variable', fg='yellow')
            click.secho('Could not find the repository name on gitlab - defaulting to demisto/content', fg='yellow')
            self.is_gitlab = False
            self.CURRENT_REPOSITORY = GitContentConfig.CURRENT_REPOSITORY
            return

        if gitlab_id:
            self.is_gitlab = True

        if self.is_gitlab:
            self.BASE_RAW_GITLAB_LINK = self.BASE_RAW_GITLAB_LINK.format(GITLAB_HOST=hostname,
                                                                         GITLAB_ID=gitlab_id)
            if not self.base_url:
                self.base_url = hostname
        else:  # github
            self.CURRENT_REPOSITORY = f'{parsed_git.owner}/{parsed_git.repo}'
            if not self.base_url or 'github.com' in self.base_url.lower():
                self.base_url = 'githubusercontent.com'

    @lru_cache(maxsize=10)
    def _search_gitlab_id(self, gitlab_hostname: str, repo: str) -> Optional[int]:
        try:
            res = requests.get(f"https://{gitlab_hostname}/api/v4/projects",
                               params={'search': repo},
                               headers={'PRIVATE-TOKEN': self.Credentials.GITLAB_TOKEN},
                               timeout=10,
                               verify=False)
            if not res.ok:
                return None
            search_results = res.json()
            return search_results[0].get('id', None) if search_results else None
        except Exception:
            return None
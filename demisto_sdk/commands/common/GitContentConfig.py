from functools import lru_cache
from typing import Iterable, Optional
from urllib.parse import urlparse

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
    BASE_RAW_GITHUB_LINK = r'https://raw.githubusercontent.com/'
    SDK_API_GITHUB_RELEASES = r'https://api.github.com/repos/demisto/demisto-sdk/releases'
    OFFICIAL_CONTENT_REPO_NAME = 'demisto/content'
    CONTENT_GITHUB_UPSTREAM = r'upstream.*demisto/content'
    CONTENT_GITHUB_ORIGIN = r'origin.*demisto/content'

    CURRENT_REPOSITORY: str
    CONTENT_GITHUB_LINK: str
    CONTENT_GITHUB_MASTER_LINK: str

    GITLAB_HOST: Optional[str] = None
    GITLAB_ID: Optional[int] = None
    BASE_RAW_GITLAB_LINK = "https://{GITLAB_HOST}/api/v4/projects/{GITLAB_ID}/repository"

    def __init__(self, repo_name: Optional[str] = None):
        self.Credentials = GitCredentials()
        if not repo_name:
            try:
                urls = list(GitUtil().repo.remote().urls)
                parsed_git = self._get_repository_properties(urls)
                self._set_repo_config(parsed_git)
            except (InvalidGitRepositoryError, AttributeError):  # No repository
                self.CURRENT_REPOSITORY = self.OFFICIAL_CONTENT_REPO_NAME
        else:
            self.CURRENT_REPOSITORY = repo_name
        if not self.GITLAB_ID:
            # DO NOT USE os.path.join on URLs, it may cause errors
            self.CONTENT_GITHUB_LINK = urljoin(self.BASE_RAW_GITHUB_LINK, self.CURRENT_REPOSITORY)
            self.CONTENT_GITHUB_MASTER_LINK = urljoin(self.CONTENT_GITHUB_LINK, r'master')

    def _get_repository_properties(self, urls: Iterable) -> Optional[giturlparse.result.GitUrlParsed]:
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
        if parsed_git.github:
            self.CURRENT_REPOSITORY = f'{parsed_git.owner}/{parsed_git.repo}'
        elif parsed_git.gitlab:
            gitlab_host = urlparse(parsed_git.url).hostname
            gitlab_id = self._search_gitlab_id(gitlab_host, parsed_git.repo)
            if gitlab_id is None:
                # default to content repo if the id is not found
                click.secho('Could not find repository id in gitlab - defaulting to demisto/content', fg='yellow')
                self.CURRENT_REPOSITORY = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
                return
            self.GITLAB_HOST = gitlab_host
            self.GITLAB_ID = gitlab_id
            self.CURRENT_REPOSITORY = parsed_git.repo
            self.BASE_RAW_GITLAB_LINK = self.BASE_RAW_GITLAB_LINK.format(GITLAB_HOST=gitlab_host,
                                                                         GITLAB_ID=gitlab_id)

        else:
            # default to content repo if the id is not found
            click.secho('Not in gitlab or github - defaulting to demisto/content', fg='yellow')
            self.CURRENT_REPOSITORY = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME

    @lru_cache(maxsize=10)
    def _search_gitlab_id(self, github_hostname: str, repo: str) -> Optional[int]:
        res = requests.get(f"https://{github_hostname}/api/v4/projects",
                           params={'search': repo},
                           headers={'PRIVATE-TOKEN': self.Credentials.GITHUB_TOKEN},
                           timeout=10,
                           verify=False)
        res.raise_for_status()
        res = res.json()
        return res[0].get('id', None) if res else None

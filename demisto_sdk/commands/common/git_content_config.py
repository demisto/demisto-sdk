"""
This is module to store the git configuration of the content repo
"""
import enum
import os
from functools import lru_cache
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

import giturlparse

# dirs
import requests

from demisto_sdk.commands.common.constants import (
    DEMISTO_SDK_CI_SERVER_HOST,
    DEMISTO_SDK_OFFICIAL_CONTENT_PROJECT_ID,
    DOCKERFILES_INFO_REPO,
)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger


class GitProvider(enum.Enum):
    GitHub = "github"
    GitLab = "gitlab"


class GitCredentials:
    ENV_GITHUB_TOKEN_NAME = "DEMISTO_SDK_GITHUB_TOKEN"
    ENV_GITLAB_TOKEN_NAME = "DEMISTO_SDK_GITLAB_TOKEN"

    def __init__(self):
        self.github_token = os.getenv(self.ENV_GITHUB_TOKEN_NAME, "")
        self.gitlab_token = os.getenv(self.ENV_GITLAB_TOKEN_NAME, "")


class GitContentConfig:
    """Holds links, credentials and other content related github configuration

    Attributes:
        credentials: Credentials to the git.
    """

    BASE_RAW_GITHUB_LINK = r"https://raw.{GITHUB_HOST}/"
    SDK_API_GITHUB_RELEASES = (
        r"https://api.github.com/repos/demisto/demisto-sdk/releases"
    )
    OFFICIAL_CONTENT_REPO_NAME = "demisto/content"
    CONTENT_GITHUB_UPSTREAM = r"upstream.*demisto/content"
    CONTENT_GITHUB_ORIGIN = r"origin.*demisto/content"
    GITHUB_USER_CONTENT = "githubusercontent.com"

    GITHUB = "github.com"
    GITLAB = "gitlab.com"

    BASE_RAW_GITLAB_LINK = (
        "https://{GITLAB_HOST}/api/v4/projects/{GITLAB_ID}/repository"
    )

    ENV_REPO_HOSTNAME_NAME = "DEMISTO_SDK_REPO_HOSTNAME"

    GITHUB_TO_USERCONTENT = {GITHUB: GITHUB_USER_CONTENT}
    USERCONTENT_TO_GITHUB = {GITHUB_USER_CONTENT: GITHUB}

    ALLOWED_REPOS = {
        (GITHUB_USER_CONTENT, OFFICIAL_CONTENT_REPO_NAME),
        (GITHUB, OFFICIAL_CONTENT_REPO_NAME),
        (DEMISTO_SDK_CI_SERVER_HOST, DEMISTO_SDK_OFFICIAL_CONTENT_PROJECT_ID),
        (GITHUB_USER_CONTENT, DOCKERFILES_INFO_REPO),
    }

    CREDENTIALS = GitCredentials()
    NOTIFIED_PRIVATE_REPO = (
        False  # to avoid multiple prints, it's set to True when printing.
    )

    def __init__(
        self,
        repo_name: Optional[str] = None,
        git_provider: Optional[GitProvider] = GitProvider.GitHub,
        repo_hostname: Optional[str] = None,
        project_id: Optional[int] = None,
    ):
        """
        Args:
            repo_name: Name of the repo (e.g "demisto/content")
            git_provider: The git provider to use (e.g GitProvider.GitHub, GitProvider.GitLab)
            repo_hostname: The hostname to use (e.g "code.pan.run", "gitlab.com", "my-hostename.com")
            project_id: The project id, relevant for gitlab.
        """
        self.current_repository = repo_name if repo_name else None
        self.project_id: Optional[int] = None
        if project_id:
            git_provider = GitProvider.GitLab
            self.project_id = int(project_id)
        hostname = urlparse(repo_hostname).hostname
        self.repo_hostname = (
            hostname
            or repo_hostname
            or os.getenv(GitContentConfig.ENV_REPO_HOSTNAME_NAME)
        )
        self.git_provider = git_provider
        if not self.repo_hostname:
            self.repo_hostname = (
                GitContentConfig.GITHUB_USER_CONTENT
                if git_provider == GitProvider.GitHub
                else GitContentConfig.GITLAB
            )
        self.repo_hostname = GitContentConfig.GITHUB_TO_USERCONTENT.get(self.repo_hostname, self.repo_hostname)  # type: ignore[arg-type]

        parsed_git = GitContentConfig._get_repository_properties()

        if parsed_git is None:
            hostname = self.repo_hostname
            organization = None
            repo_name = self.current_repository
        else:
            hostname = parsed_git.host
            organization = parsed_git.owner
            repo_name = parsed_git.repo
            if (
                "@" in parsed_git.host
            ):  # the library sometimes returns hostname as <username>@<hostname>
                hostname = parsed_git.host.split("@")[
                    1
                ]  # to get proper hostname, without the username or tokens
        if (
            self.repo_hostname,
            self.current_repository,
        ) not in GitContentConfig.ALLOWED_REPOS and (
            self.repo_hostname,
            self.project_id,
        ) not in GitContentConfig.ALLOWED_REPOS:
            self._set_repo_config(hostname, organization, repo_name, project_id)  # type: ignore[arg-type]

        if self.git_provider == GitProvider.GitHub:
            # DO NOT USE os.path.join on URLs, it may cause errors
            self.base_api = urljoin(
                GitContentConfig.BASE_RAW_GITHUB_LINK.format(
                    GITHUB_HOST=self.repo_hostname
                ),
                self.current_repository,
            )
        else:  # gitlab
            self.base_api = GitContentConfig.BASE_RAW_GITLAB_LINK.format(
                GITLAB_HOST=self.repo_hostname, GITLAB_ID=self.project_id
            )

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
            return None
        except Exception as e:
            logger.warning(
                f"Could not get repository properties: {e}, using provided configs, or default."
            )
            return None

    def _set_repo_config(
        self,
        hostname: str,
        organization: str = None,
        repo_name: str = None,
        project_id: int = None,
    ):
        """
        Set repository config.
        Search the repository on gitlab or gitlab APIs to check if exists.
        If not, defaults to demisto/content.

        Args:
            hostname (str): The hostname of the repo
            organization (str, optional): The organization of the repo. Defaults to None.
            repo_name (str, optional): The repo name. Defaults to None.
            project_id (int, optional): The repo id. Defaults to None.
        """
        gitlab_hostname, gitlab_id = (
            (self._search_gitlab_repo(hostname, project_id=project_id))
            or (self._search_gitlab_repo(self.repo_hostname, project_id=project_id))
            or (self._search_gitlab_repo(hostname, repo_name=repo_name))
            or (self._search_gitlab_repo(self.repo_hostname, repo_name=repo_name))
            or (None, None)
        )

        if self.git_provider == GitProvider.GitLab and gitlab_id is None:
            self._print_private_repo_warning_if_needed()
            self.git_provider = GitProvider.GitHub
            self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
            self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT
            return

        if gitlab_id is not None:
            self.git_provider = GitProvider.GitLab
            self.project_id = gitlab_id
            self.repo_hostname = str(gitlab_hostname)
        else:  # github
            current_repo = (
                f"{organization}/{repo_name}"
                if organization and repo_name
                else self.current_repository
            )
            github_hostname, github_repo = (
                self._search_github_repo(hostname, self.current_repository)
                or self._search_github_repo(self.repo_hostname, current_repo)
                or (None, None)
            )
            self.git_provider = GitProvider.GitHub
            if not github_hostname or not github_repo:  # github was not found.
                self._print_private_repo_warning_if_needed()
                self.current_repository = GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
                self.repo_hostname = GitContentConfig.GITHUB_USER_CONTENT
            else:
                self.repo_hostname = github_hostname
                self.current_repository = github_repo

    @staticmethod
    def _print_private_repo_warning_if_needed():
        """
        Checks the class variable, prints if necessary, and sets the class variable to avoid multiple prints
        """
        if not GitContentConfig.NOTIFIED_PRIVATE_REPO:
            logger.info(
                "[yellow]Could not find the repository name on gitlab - defaulting to demisto/content[/yellow]"
            )
            logger.info(
                f"[yellow]If you are using a private gitlab repo, "
                f"configure one of the following environment variables: "
                f"`{GitCredentials.ENV_GITLAB_TOKEN_NAME}`,`{GitContentConfig.ENV_REPO_HOSTNAME_NAME}`[/yellow]"
            )
            GitContentConfig.NOTIFIED_PRIVATE_REPO = True

    @staticmethod
    @lru_cache
    def _search_github_repo(
        github_hostname: str, repo_name: str
    ) -> Optional[Tuple[str, str]]:
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
        api_host = GitContentConfig.USERCONTENT_TO_GITHUB.get(
            github_hostname, github_hostname
        ).lower()
        github_hostname = GitContentConfig.GITHUB_TO_USERCONTENT.get(
            github_hostname, github_hostname
        )
        if (api_host, repo_name) in GitContentConfig.ALLOWED_REPOS:
            return github_hostname, repo_name
        github_hostname = GitContentConfig.GITHUB_TO_USERCONTENT.get(api_host, api_host)
        try:
            r = requests.get(
                f"https://api.{api_host}/repos/{repo_name}",
                headers={
                    "Authorization": f"Bearer {GitContentConfig.CREDENTIALS.github_token}"
                    if GitContentConfig.CREDENTIALS.github_token
                    else "",
                    "Accept": "application/vnd.github.VERSION.raw",
                },
                verify=False,
                timeout=10,
            )
            if r.ok:
                return github_hostname, repo_name
            r = requests.get(
                f"https://api.{api_host}/repos/{repo_name}",
                verify=False,
                params={"token": GitContentConfig.CREDENTIALS.github_token},
                timeout=10,
            )
            if r.ok:
                return github_hostname, repo_name
            logger.debug(
                f"Could not access GitHub api in `_search_github_repo`. status code={r.status_code}, reason={r.reason}"
            )
            return None
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
        ) as e:
            logger.debug(str(e), exc_info=True)
            return None

    @staticmethod
    @lru_cache
    def _search_gitlab_repo(
        gitlab_hostname: str,
        repo_name: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> Optional[Tuple[str, int]]:
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
        if (
            not gitlab_hostname
            or gitlab_hostname == GitContentConfig.GITHUB_USER_CONTENT
            or gitlab_hostname == GitContentConfig.GITHUB
        ):
            return None
        if (
            project_id
            and (gitlab_hostname, project_id) in GitContentConfig.ALLOWED_REPOS
        ):
            return gitlab_hostname, project_id
        try:
            res = None
            if project_id:
                res = requests.get(
                    f"https://{gitlab_hostname}/api/v4/projects/{project_id}",
                    headers={
                        "PRIVATE-TOKEN": GitContentConfig.CREDENTIALS.gitlab_token
                    },
                    timeout=10,
                    verify=False,
                )
                if res.ok:
                    return gitlab_hostname, project_id

            if repo_name:
                res = requests.get(
                    f"https://{gitlab_hostname}/api/v4/projects",
                    params={"search": repo_name},
                    headers={
                        "PRIVATE-TOKEN": GitContentConfig.CREDENTIALS.gitlab_token
                    },
                    timeout=10,
                    verify=False,
                )
                if not res.ok:
                    return None
                search_results = res.json()
                assert (
                    search_results
                    and isinstance(search_results, list)
                    and isinstance(search_results[0], dict)
                )
                gitlab_id = search_results[0].get("id")
                if gitlab_id is None:
                    return None
                return gitlab_hostname, gitlab_id
            logger.debug("Could not access GitLab api in `_search_gitlab_repo`.")
            if res:
                logger.debug(f"status code={res.status_code}. reason={res.reason}")
            return None

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout,
            json.JSONDecodeError,
            AssertionError,
        ) as e:
            logger.debug(str(e), exc_info=True)
            return None

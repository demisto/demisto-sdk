import os
from typing import NamedTuple

import click
import pytest
from git import Repo

from demisto_sdk.commands.common.git_content_config import (
    GitContentConfig,
    GitCredentials,
    GitProvider,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path

json = JSON_Handler()
GIT_ROOT = git_path()
VALID_GITLAB_RESPONSE = (
    f"{GIT_ROOT}/demisto_sdk/tests/test_files/valid_gitlab_search_response.json"
)

DEFAULT_GITHUB_BASE_API = "https://raw.githubusercontent.com/demisto/content"


class Urls(NamedTuple):
    urls: list


class TestGitContentConfig:
    @staticmethod
    def teardown_method():
        # runs after each method, making sure tests do not interfere
        GitContentConfig.NOTIFIED_PRIVATE_REPO = False

    @pytest.mark.parametrize(
        "url, repo_name",
        [
            ("ssh://git@github.com/demisto/content-dist.git", "demisto/content-dist"),
            ("git@github.com:demisto/content-dist.git", "demisto/content-dist"),
            # clone using github ssh example
            ("https://github.com/demisto/content-dist.git", "demisto/content-dist"),
            # clone using github https example
            ("https://github.com/demisto/content-dist", "demisto/content-dist"),
        ],
    )
    def test_valid_githubs(self, mocker, requests_mock, url: str, repo_name):
        """
        Given:
            valid github remote urls
        When:
            Trying to get github configuration
        Then:
            Validate the correct repo configuration got back
        """
        mocker.patch.object(GitContentConfig, "_search_gitlab_repo", return_value=None)
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))
        requests_mock.get(f"https://api.github.com/repos/{repo_name}")
        git_config = GitContentConfig()
        assert git_config.current_repository == repo_name
        assert "githubusercontent.com" in git_config.base_api

    @pytest.mark.parametrize(
        "url, repo_name",
        [
            ("https://code.pan.run/xsoar/content-dist", "xsoar/content-dist"),  # gitlab
            ("https://code.pan.run/xsoar/content-dist.git", "xsoar/content-dist"),
            (
                "https://gitlab-ci-token:token@code.pan.run/xsoar/content-dist.git",
                "xsoar/content-dist",
            ),
        ],
    )
    def test_valid_gitlabs(self, mocker, requests_mock, url, repo_name):
        """
        Given:
            valid gitlab remote urls
        When:
            Trying to get git configuration
        Then:
            Validate the correct repo configuration got back
        """
        requests_mock.get("https://code.pan.run/api/v4/projects", json=[{"id": 3606}])
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))
        git_config = GitContentConfig()
        assert (
            git_config.current_repository is None
        )  # does not relevant to gitlab at all
        assert git_config.git_provider == GitProvider.GitLab
        assert git_config.base_api == GitContentConfig.BASE_RAW_GITLAB_LINK.format(
            GITLAB_HOST="code.pan.run", GITLAB_ID=3606
        )

        # We give the repo hostname, but there is a response from the remote url hostname
        git_config = GitContentConfig(
            repo_hostname="my-gitlab-hostname.com", git_provider=GitProvider.GitLab
        )
        assert git_config.base_api == GitContentConfig.BASE_RAW_GITLAB_LINK.format(
            GITLAB_HOST="code.pan.run", GITLAB_ID=3606
        )

    def test_custom_github_url(self, mocker, requests_mock):
        """
        Given:
            A github remote url and the environment variable is set
        When:
            Trying to get git configuration
        Then:
            Validate the correct repo configuration got back
        """
        mocker.patch.object(GitContentConfig, "_search_gitlab_repo", return_value=None)
        custom_github = "my-own-github-url.com"
        repo_name = "org/repo"
        requests_mock.get(f"https://api.{custom_github}/repos/{repo_name}")
        url = f"https://{custom_github}/{repo_name}"
        mocker.patch.dict(
            os.environ, {GitContentConfig.ENV_REPO_HOSTNAME_NAME: custom_github}
        )  # test with env var
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))
        git_config = GitContentConfig()
        assert git_config.git_provider == GitProvider.GitHub
        assert git_config.current_repository == "org/repo"
        assert git_config.base_api == f"https://raw.{custom_github}/org/repo"

        mocker.patch.dict(os.environ, {})
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))
        git_config = GitContentConfig(repo_hostname=custom_github)  # test with argument
        assert git_config.git_provider == GitProvider.GitHub
        assert git_config.current_repository == "org/repo"
        assert git_config.base_api == f"https://raw.{custom_github}/org/repo"

        # test with no args, should find it with remote address
        git_config = GitContentConfig()  # test with argument
        assert git_config.git_provider == GitProvider.GitHub
        assert git_config.current_repository == "org/repo"
        assert git_config.base_api == f"https://raw.{custom_github}/org/repo"

    def test_custom_github_url_invalid(self, mocker, requests_mock):
        """
        Given:
            A github remote url but the repo is not exists
        When:
            Trying to get git configuration
        Then:
            Validate we got back original content
        """
        mocker.patch.object(GitContentConfig, "_search_gitlab_repo", return_value=None)
        custom_github = "my-own-github-url.com"
        repo_name = "org/repo"
        requests_mock.get(
            f"https://api.{custom_github}/repos/{repo_name}", status_code=404
        )
        requests_mock.get(f"https://api.github.com/repos/{repo_name}", status_code=404)
        url = f"https://{custom_github}/{repo_name}"
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))
        git_config = GitContentConfig()
        assert (
            git_config.current_repository == GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        )
        assert git_config.base_api == DEFAULT_GITHUB_BASE_API

    def test_gitlab_id_not_found(self, mocker):
        """
        Given:
            Specify to use gitlab but cannot find the project id
        When:
            Trying to get git configuration
        Then:
            Validate we got back original content
        """
        mocker.patch.object(GitContentConfig, "_search_gitlab_repo", return_value=None)
        url = "https://code.pan.run/xsoar/very-private-repo"
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))
        click_mock = mocker.patch.object(click, "secho")
        git_config = GitContentConfig(git_provider=GitProvider.GitLab)
        assert git_config.git_provider == GitProvider.GitHub
        assert (
            git_config.current_repository == GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        )
        assert git_config.base_api == DEFAULT_GITHUB_BASE_API
        message = click_mock.call_args_list[1][0][0]
        assert GitContentConfig.ENV_REPO_HOSTNAME_NAME in message
        assert GitCredentials.ENV_GITLAB_TOKEN_NAME in message
        assert GitContentConfig.NOTIFIED_PRIVATE_REPO

    def test_get_repo_name_gitlab_invalid(self, mocker):
        """
        Given:
            No repository (not running in git)
        When:
            A known output of git.Repo().remotes().url, but this url not found in GitLab API
        Then:
            Ignore gitlab and get back to content (demisto/content)
        """
        url = "https://code.pan.run/xsoar/very-private-repo"
        mocker.patch.object(Repo, "remote", return_value=Urls([url]))

        mocker.patch.object(GitContentConfig, "_search_gitlab_repo", return_value=None)
        git_config = GitContentConfig()
        # for invalid response should return the official content repo
        assert (
            git_config.current_repository == GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        )

    def test_get_repo_name_empty_case(self, mocker):
        """
        Given:
            No repository (not running in git)
        When:
            Searching for repository name
        Then:
            Validate the correct repo got back - demisto/content
        """
        mocker.patch.object(Repo, "remote", return_value=Urls([""]))
        mocker.patch.object(GitContentConfig, "_search_github_repo", return_value=None)
        git_config = GitContentConfig()
        assert (
            git_config.current_repository == GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        )

    def test_search_gitlab_id_valid(self, mocker, requests_mock):
        """
        Given:
            A valid repo name
        When:
            Searching for the id of the repo
        Then:
            The id of the repo should be returned
        """

        with open(VALID_GITLAB_RESPONSE) as f:
            gitlab_response = json.load(f)
        repo = "content-internal-dist"
        host = "code.pan.run"
        url = f"https://{host}/api/v4/projects?search={repo}"
        requests_mock.get(url, json=gitlab_response)
        mocker.patch.object(
            Repo,
            "remote",
            return_value=Urls(["https://code.pan.run/xsoar/content-internal-dist.git"]),
        )
        git_config = GitContentConfig()
        assert (
            git_config.project_id == 3606
        )  # this is the project id of `content-internal-dist`
        assert git_config.base_api == GitContentConfig.BASE_RAW_GITLAB_LINK.format(
            GITLAB_HOST=host, GITLAB_ID=3606
        )

    def test_search_gitlab_id_invalid(self, mocker, requests_mock):
        """
        Given:
            An invalid repo name
        When:
            Searching for the id of the repo
        Then:
            None should be returned
        """

        repo = "no-real-repo"
        host = "code.pan.run"
        search_api_url1 = f"https://code.pan.run/api/v4/projects?search={repo}"
        search_api_url2 = "https://code.pan.run/api/v4/projects?search=test"

        requests_mock.get(search_api_url1, json=[])
        requests_mock.get(search_api_url2, json=[])
        mocker.patch.object(
            Repo, "remote", return_value=Urls(["https://code.pan.run/xsoar/test"])
        )
        mocker.patch.object(GitContentConfig, "_search_github_repo", return_value=None)
        git_config = GitContentConfig()
        assert git_config._search_gitlab_repo(host, repo) is None
        assert (
            git_config.current_repository == GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        )
        assert git_config.git_provider == GitProvider.GitHub
        assert git_config.base_api == DEFAULT_GITHUB_BASE_API

    def test_provide_repo_name(self, mocker, requests_mock):
        """
        Given:
            A repo name argument to git config
        When:
            Calling git config to other repo instead of the one that configured in the env
        Then:
            The git config should be as the repo name provided
        """

        requests_mock.get(
            f"https://api.github.com/repos/{GitContentConfig.OFFICIAL_CONTENT_REPO_NAME}"
        )
        git_config = GitContentConfig(GitContentConfig.OFFICIAL_CONTENT_REPO_NAME)
        assert (
            git_config.current_repository == GitContentConfig.OFFICIAL_CONTENT_REPO_NAME
        )
        assert git_config.base_api == DEFAULT_GITHUB_BASE_API

        custom_repo_name = "org/repo"
        requests_mock.get(f"https://api.github.com/repos/{custom_repo_name}")
        requests_mock.get("https://api.github.com/repos/demisto/demisto-sdk")
        git_config = GitContentConfig(custom_repo_name)

        assert git_config.current_repository == custom_repo_name
        assert (
            git_config.base_api
            == f"https://raw.githubusercontent.com/{custom_repo_name}"
        )

        mocker.patch.object(
            GitContentConfig, "_search_gitlab_repo", return_value=("gitlab.com", 3)
        )
        git_config = GitContentConfig(custom_repo_name, git_provider=GitProvider.GitLab)
        assert git_config.current_repository == custom_repo_name
        assert git_config.base_api == "https://gitlab.com/api/v4/projects/3/repository"

    def test_provide_project_id(self, requests_mock):
        """
        Given:
            Project id to gitlab
        When:
            Calling git config with repo based on gitlab
        Then:
            The git config should be as the repo name provided
        """
        requests_mock.get("https://code.pan.run/api/v4/projects/3")
        git_config = GitContentConfig(
            project_id=3, git_provider=GitProvider.GitLab, repo_hostname="code.pan.run"
        )
        assert git_config.project_id == 3
        assert (
            git_config.base_api == "https://code.pan.run/api/v4/projects/3/repository"
        )

from typing import Optional

import pytest

from demisto_sdk.commands.common.hook_validations.readme import ReadmeUrl
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.format.update_readme import ReadmeFormat

INVALID_MD = f"{git_path()}/demisto_sdk/tests/test_files/README-invalid.md"
INVALID_MD_IN_PACK = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack2"


def test_format_wit_update_docker_flag(mocker):
    """
    Check when run demisto-sdk format execute with -ud (update docker) from repo which does not have a mdx server,
    (but has a node), that the run ends without any exception.
    """
    from demisto_sdk.commands.common.git_util import GitUtil
    from demisto_sdk.commands.common.hook_validations.readme import ReadMeValidator
    from demisto_sdk.commands.format.format_module import format_manager
    from demisto_sdk.commands.validate.validate_manager import ValidateManager

    mocker.patch.object(
        ReadMeValidator, "are_modules_installed_for_verify", return_value=False
    )
    mocker.patch.object(ReadMeValidator, "is_docker_available", return_value=False)
    mocker.patch.object(
        ValidateManager,
        "get_changed_files_from_git",
        return_value=(set(), set(), set(), set(), True),
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=set())
    assert format_manager(input=f"{git_path()}/Packs/TestPack", update_docker=True) == 0


def get_new_url_from_user_assume_yes(relative_url: list) -> Optional[str]:
    """Check if new url is as expected when using assume_yes flag"""
    readme_formatter = ReadmeFormat(INVALID_MD, assume_yes=True)
    return readme_formatter.get_new_url_from_user(relative_url)


def get_new_url_from_user_add_prefix(mocker, relative_url: list) -> Optional[str]:
    """Check if new url is as expected when user selects adding https:// prefix"""
    mocker.patch("builtins.input", side_effect=["y"])

    readme_formatter = ReadmeFormat(INVALID_MD)
    return readme_formatter.get_new_url_from_user(relative_url)


def get_new_url_from_user_change_url(mocker, relative_url: list) -> Optional[str]:
    """Check if new url is as expected when user inserts new url"""
    mocker.patch("builtins.input", side_effect=["n", "https://goodurl.com"])

    readme_formatter = ReadmeFormat(INVALID_MD)
    return readme_formatter.get_new_url_from_user(relative_url)


def get_new_url_from_user_skip(mocker, relative_url: list) -> Optional[str]:
    """Check if new url is as expected when user asks to skip"""
    mocker.patch("builtins.input", side_effect=["n", ""])

    readme_formatter = ReadmeFormat(INVALID_MD)
    return readme_formatter.get_new_url_from_user(relative_url)


class TestReadmeFormat:
    @pytest.mark.parametrize(
        "regex_relative_url,new_url,expected_link",
        (
            (
                ["[invalid relative 2]", "www.relative2.com", True],
                "https://new.com",
                "[invalid relative 2](https://new.com)",
            ),
            (
                ['<a href="www.hreftesting.com"', "www.hreftesting.com", False],
                "https://new.com",
                '<a href="https://new.com"',
            ),
        ),
    )
    def test_replace_url_in_content(
        self, regex_relative_url: list, new_url: str, expected_link: str
    ):
        """
        Given
            - A README file , and a relative url link found in it.
        When
            - Run replace_url_in_content on it
        Then
            - Ensure the url changes to the expected output.
        """
        readme_formatter = ReadmeFormat(INVALID_MD)
        readme_url = ReadmeUrl(
            regex_relative_url[0], regex_relative_url[1], regex_relative_url[2]
        )
        readme_formatter.replace_url_in_content(readme_url, new_url)
        assert expected_link in readme_formatter.readme_content

    @pytest.mark.parametrize(
        "relative_url",
        (
            (["[invalid relative 1]", " relative1.com", True]),
            (["[invalid relative 2]", "www.relative2.com", True]),
            (['<a href="www.hreftesting.com"', "www.hreftesting.com", False]),
            (['<a href="www.hreftesting.com  "', "www.hreftesting.com  ", False]),
        ),
    )
    def test_get_new_url_from_user(self, mocker, relative_url: list):
        """
        Given
            - A relative url, sometimes with trailing spaces.
            check the following scenarios-
            (A) - assume-yes flag is on.
            (B) - request to add prefix.
            (C) - request to change url.
            (D) - request to skip.
        When
            - Run get_new_url_from_user.
        Then
            - Ensure the new url is as expected.
            (A) - https:// is added to address.
            (B) - https:// is added to address.
            (C) - New url is returned.
            (D) - None is returned.
        """
        stripped_url = str.strip(relative_url[1])
        readme_url = ReadmeUrl(relative_url[0], relative_url[1], relative_url[2])
        assert get_new_url_from_user_assume_yes(readme_url) == f"https://{stripped_url}"
        assert (
            get_new_url_from_user_add_prefix(mocker, readme_url)
            == f"https://{stripped_url}"
        )
        assert (
            get_new_url_from_user_change_url(mocker, readme_url)
            == "https://goodurl.com"
        )
        assert get_new_url_from_user_skip(mocker, readme_url) is None

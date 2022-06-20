from typing import Optional

import pytest

from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.format.update_readme import ReadmeFormat

INVALID_MD = f'{git_path()}/demisto_sdk/tests/test_files/README-invalid.md'
INVALID_MD_IN_PACK = f'{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack2'


def get_new_url_from_user_assume_yes(relative_url: list) -> Optional[str]:
    """Check if new url is as expected when using assume_yes flag"""
    readme_formatter = ReadmeFormat(INVALID_MD, assume_yes=True)
    return readme_formatter.get_new_url_from_user(relative_url)


def get_new_url_from_user_add_prefix(mocker, relative_url: list) -> Optional[str]:
    """Check if new url is as expected when user selects adding https:// prefix"""
    mocker.patch('builtins.input', side_effect=['y'])

    readme_formatter = ReadmeFormat(INVALID_MD)
    return readme_formatter.get_new_url_from_user(relative_url)


def get_new_url_from_user_change_url(mocker, relative_url: list) -> Optional[str]:
    """Check if new url is as expected when user inserts new url"""
    mocker.patch('builtins.input', side_effect=['n', 'https://goodurl.com'])

    readme_formatter = ReadmeFormat(INVALID_MD)
    return readme_formatter.get_new_url_from_user(relative_url)


def get_new_url_from_user_skip(mocker, relative_url: list) -> Optional[str]:
    """Check if new url is as expected when user asks to skip"""
    mocker.patch('builtins.input', side_effect=['n', ''])

    readme_formatter = ReadmeFormat(INVALID_MD)
    return readme_formatter.get_new_url_from_user(relative_url)


class TestReadmeFormat:
    @pytest.mark.parametrize('regex_relative_url,new_url,expected_link',
                             ((['[invalid relative 2]', 'www.relative2.com'], 'https://new.com',
                               '[invalid relative 2](https://new.com)'), (
                              ['<a href="www.hreftesting.com"', 'www.hreftesting.com'], 'https://new.com',
                              '<a href="https://new.com"'),
                              )
                             )
    def test_replace_url_in_content(self, regex_relative_url: list, new_url: str, expected_link: str):
        """
        Given
            - A README file , and a relative url link found in it.
        When
            - Run replace_url_in_content on it
        Then
            - Ensure the url changes to the expected output.
        """
        readme_formatter = ReadmeFormat(INVALID_MD)
        readme_formatter.replace_url_in_content(regex_relative_url, new_url)
        assert expected_link in readme_formatter.readme_content

    @pytest.mark.parametrize('relative_url',
                             ((['[invalid relative 1]', ' relative1.com']),
                              (['[invalid relative 2]', 'www.relative2.com']),
                              (['<a href="www.hreftesting.com"', 'www.hreftesting.com']),
                              (['<a href="www.hreftesting.com  "', 'www.hreftesting.com  ']),
                              )
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
        assert get_new_url_from_user_assume_yes(relative_url) == f'https://{stripped_url}'
        assert get_new_url_from_user_add_prefix(mocker, relative_url) == f'https://{stripped_url}'
        assert get_new_url_from_user_change_url(mocker, relative_url) == 'https://goodurl.com'
        assert get_new_url_from_user_skip(mocker, relative_url) is None

    def test_get_relative_urls(self):
        """
        Given
            - A README file , with relative url links in it.
        When
            - Run get_relative_urls.
        Then
            - Ensure that all urls were caught, absolute url and empty links were not.
        """
        absolute_urls = ["https://www.good.co.il", "https://example.com", "https://github.com/demisto/content/blob/123",
                         "/Packs/FeedOffice365/doc_files/test.png", "https://hreftesting.com", ""]
        relative_urls = ["relative1.com", "www.relative2.com", "hreftesting.com", "www.hreftesting.com"]
        readme_formatter = ReadmeFormat(INVALID_MD)
        found_relative_regex = readme_formatter.get_relative_urls()
        found_relative_url = [url[1] for url in found_relative_regex]
        for url in absolute_urls:
            assert url not in found_relative_url

        for url in relative_urls:
            assert url in found_relative_url

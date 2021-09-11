import json
import os

import click
import pytest
import requests_mock
from click.testing import CliRunner
from git import GitCommandError

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (PACK_METADATA_DESC,
                                                   PACK_METADATA_SUPPORT,
                                                   PACK_METADATA_TAGS,
                                                   PACK_METADATA_USE_CASES,
                                                   PACKS_README_FILE_NAME,
                                                   XSOAR_SUPPORT)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from TestSuite.test_tools import ChangeCWD

VALIDATE_CMD = "validate"
PACK_METADATA_PARTNER = {
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": [],
    "price": 2,
    "email": "some@mail.com",
    "url": "https://www.paloaltonetworks.com/cortex"
}

README_INPUT_RESULTS_LIST = [
    ('', False),
    (' ', False),
    ('\t\t\n ', False),
    ('Text', True),
]


class TestPackUniqueFilesValidator:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files', 'Packs'))
    FAKE_PACK_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files',
                                                   'fake_pack'))
    FAKE_PATH_NAME = 'fake_pack'
    FAKE_PACK_PATH = os.path.join(FILES_PATH, FAKE_PATH_NAME)
    validator = PackUniqueFilesValidator(FAKE_PATH_NAME)
    validator.pack_path = FAKE_PACK_PATH

    def restart_validator(self):
        self.validator.pack_path = ''
        self.validator = PackUniqueFilesValidator(self.FAKE_PATH_NAME)
        self.validator.pack_path = self.FAKE_PACK_PATH

    def test_is_error_added_name_only(self):
        self.validator._add_error(('boop', '101'), 'file_name')
        assert f'{self.validator.pack_path}/file_name: [101] - boop\n' in self.validator.get_errors(True)
        assert f'{self.validator.pack_path}/file_name: [101] - boop\n' in self.validator.get_errors()
        self.validator._errors = []

    def test_is_error_added_full_path(self):
        self.validator._add_error(('boop', '101'), f'{self.validator.pack_path}/file/name')
        assert f'{self.validator.pack_path}/file/name: [101] - boop\n' in self.validator.get_errors(True)
        assert f'{self.validator.pack_path}/file/name: [101] - boop\n' in self.validator.get_errors()
        self.validator._errors = []

    def test_is_file_exist(self):
        assert self.validator._is_pack_file_exists(PACKS_README_FILE_NAME)
        assert not self.validator._is_pack_file_exists('boop')
        self.validator._errors = []

    def test_parse_file_into_list(self):
        assert ['boop', 'sade', ''] == self.validator._parse_file_into_list(PACKS_README_FILE_NAME)
        assert not self.validator._parse_file_into_list('boop')
        self.validator._errors = []

    def test_validate_pack_unique_files(self, mocker):
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_readme_and_pack_description', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_readme_images', return_value=True)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        assert not self.validator.are_valid_files(id_set_validations=False)
        fake_validator = PackUniqueFilesValidator('fake')
        mocker.patch.object(fake_validator, '_read_metadata_content', return_value=dict())
        assert fake_validator.are_valid_files(id_set_validations=False)

    def test_validate_pack_metadata(self, mocker):
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_readme_and_pack_description', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_readme_images', return_value=True)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        assert not self.validator.are_valid_files(id_set_validations=False)
        fake_validator = PackUniqueFilesValidator('fake')
        mocker.patch.object(fake_validator, '_read_metadata_content', return_value=dict())
        assert fake_validator.are_valid_files(id_set_validations=False)

    def test_validate_partner_contribute_pack_metadata_no_mail_and_url(self, mocker, repo):
        """
        Given
        - Partner contributed pack without email and url.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        pack_metadata_no_email_and_url = PACK_METADATA_PARTNER.copy()
        pack_metadata_no_email_and_url['email'] = ''
        pack_metadata_no_email_and_url['url'] = ''
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, 'get_master_private_repo_meta_file', return_value=None)
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=json.dumps(pack_metadata_no_email_and_url))
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value=None)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        pack = repo.create_pack('PackName')
        pack.pack_metadata.write_json(pack_metadata_no_email_and_url)
        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', pack.path], catch_exceptions=False)
        assert 'Contributed packs must include email or url' in result.stdout

    @pytest.mark.parametrize('url, is_valid', [
        ('https://github.com/pont_to_repo', False),
        ('some_support_url', True),
        ('https://github.com/pont_to_repo/issues', True),
    ])
    def test_validate_partner_pack_metadata_url(self, mocker, repo, url, is_valid):
        """
        Given
        - Partner contributed pack with an is_valid url.

        When
        - Running validate on it.

        Then
        - Ensure validate finds errors accordingly.
        """
        pack_metadata_changed_url = PACK_METADATA_PARTNER.copy()
        pack_metadata_changed_url['url'] = url

        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, 'get_master_private_repo_meta_file', return_value=None)
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=json.dumps(pack_metadata_changed_url))
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value=None)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        pack = repo.create_pack('PackName')
        pack.pack_metadata.write_json(pack_metadata_changed_url)
        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', pack.path], catch_exceptions=False)

        error_text = 'The metadata URL leads to a GitHub repo instead of a support page.'
        if is_valid:
            assert error_text not in result.stdout
        else:
            assert error_text in result.stdout

    def test_validate_partner_contribute_pack_metadata_price_change(self, mocker, repo):
        """
        Given
        - Partner contributed pack where price has changed.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        pack_metadata_price_changed = PACK_METADATA_PARTNER.copy()
        pack_metadata_price_changed['price'] = 3
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, 'get_master_private_repo_meta_file',
                            return_value=PACK_METADATA_PARTNER)
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=json.dumps(pack_metadata_price_changed))
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value=None)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        pack = repo.create_pack('PackName')
        pack.pack_metadata.write_json(pack_metadata_price_changed)
        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', pack.path], catch_exceptions=False)
        assert 'The pack price was changed from 2 to 3 - revert the change' in result.stdout

    def test_check_timestamp_format(self):
        """
        Given
        - timestamps in various formats.

        When
        - Running check_timestamp_format on them.

        Then
        - Ensure True for iso format and False for any other format.
        """
        fake_validator = PackUniqueFilesValidator('fake')
        good_format_timestamp = '2020-04-14T00:00:00Z'
        missing_z = '2020-04-14T00:00:00'
        missing_t = '2020-04-14 00:00:00Z'
        only_date = '2020-04-14'
        with_hyphen = '2020-04-14T00-00-00Z'
        assert fake_validator.check_timestamp_format(good_format_timestamp)
        assert not fake_validator.check_timestamp_format(missing_t)
        assert not fake_validator.check_timestamp_format(missing_z)
        assert not fake_validator.check_timestamp_format(only_date)
        assert not fake_validator.check_timestamp_format(with_hyphen)

    def test_validate_pack_dependencies_invalid_id_set(self, mocker, repo):
        """
        Given
        - An invalid id set error being raised

        When
        - Running validate_pack_dependencies.

        Then
        - Ensure that the validation fails and that the invalid id set error is printed.
        """
        self.restart_validator()

        def error_raising_function(*args, **kwargs):
            raise ValueError("Couldn't find any items for pack 'PackID'. make sure your spelling is correct.")

        mocker.patch(
            'demisto_sdk.commands.common.hook_validations.pack_unique_files.get_core_pack_list',
            side_effect=error_raising_function
        )
        assert not self.validator.validate_pack_dependencies()
        assert Errors.invalid_id_set()[0] in self.validator.get_errors()

    def test_validate_core_pack_dependencies(self):
        """
        Given
        - A list of non-core packs

        When
        - Running validate_core_pack_dependencies.

        Then
        - Ensure that the validation fails and that the invalid core pack dependencies error is printed.
        """
        self.restart_validator()
        dependencies_packs = {'dependency_pack_1': {'mandatory': True, 'display_name': 'dependency pack 1'},
                              'dependency_pack_2': {'mandatory': False, 'display_name': 'dependency pack 2'},
                              'dependency_pack_3': {'mandatory': True, 'display_name': 'dependency pack 3'}}

        assert not self.validator.validate_core_pack_dependencies(dependencies_packs)
        assert Errors.invalid_core_pack_dependencies('fake_pack', ['dependency_pack_1', 'dependency_pack_3'])[0] \
            in self.validator.get_errors()

    def test_validate_pack_dependencies_skip_id_set_creation(self, capsys):
        """
        Given
        -  skip_id_set_creation flag set to true.
        -  No id_set file exists

        When
        - Running validate_pack_dependencies.

        Then
        - Ensure that the validation passes and that the skipping message is printed.
        """
        self.restart_validator()
        self.validator.skip_id_set_creation = True
        res = self.validator.validate_pack_dependencies()
        self.validator.skip_id_set_creation = False  # reverting to default for next tests
        assert res
        assert "No first level dependencies found" in capsys.readouterr().out

    @pytest.mark.parametrize('usecases, is_valid, branch_usecases', [
        ([], True, []),
        (['Phishing', 'Malware'], True, []),
        (['NonApprovedUsecase', 'Case Management'], False, []),
        (['NewUseCase'], True, ['NewUseCase']),
        (['NewUseCase1, NewUseCase2'], False, ['NewUseCase1'])
    ])
    def test_is_approved_usecases(self, repo, usecases, is_valid, branch_usecases, mocker):
        """
        Given:
            - Case A: Pack without usecases
            - Case B: Pack with approved usecases (Phishing and Malware)
            - Case C: Pack with non-approved usecase (NonApprovedUsecase) and approved usecase (Case Management)
            - Case D: Pack with approved usecase (NewUseCase) located in my branch only
            - Case E: Pack with non-approved usecase (NewUseCase2) and approved usecase (NewUseCase1)
            located in my branch only

        When:
            - Validating approved usecases

        Then:
            - Case A: Ensure validation passes as there are no usecases to verify
            - Case B: Ensure validation passes as both usecases are approved
            - Case C: Ensure validation fails as it contains a non-approved usecase (NonApprovedUsecase)
                      Verify expected error is printed
            - Case D: Ensure validation passes as usecase is approved on the same branch
            - Case E: Ensure validation fails as it contains a non-approved usecase (NewUseCase2)
                      Verify expected error is printed
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json({
            PACK_METADATA_USE_CASES: usecases,
            PACK_METADATA_SUPPORT: XSOAR_SUPPORT,
            PACK_METADATA_TAGS: []
        })
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': branch_usecases}, 'json'))
        self.validator.pack_path = pack.path

        with ChangeCWD(repo.path):
            assert self.validator._is_approved_usecases() == is_valid
            if not is_valid:
                assert 'The pack metadata contains non approved usecases:' in self.validator.get_errors()

    @pytest.mark.parametrize('tags, is_valid, branch_tags', [
        ([], True, []),
        (['Machine Learning', 'Spam'], True, []),
        (['NonApprovedTag', 'GDPR'], False, []),
        (['NewTag'], True, ['NewTag']),
        (['NewTag1, NewTag2'], False, ['NewTag1'])
    ])
    def test_is_approved_tags(self, repo, tags, is_valid, branch_tags, mocker):
        """
        Given:
            - Case A: Pack without tags
            - Case B: Pack with approved tags (Machine Learning and Spam)
            - Case C: Pack with non-approved tags (NonApprovedTag) and approved tags (GDPR)
            - Case D: Pack with approved tags (NewTag) located in my branch only
            - Case E: Pack with non-approved tags (NewTag) and approved tags (NewTag)
            located in my branch only
        When:
            - Validating approved tags

        Then:
            - Case A: Ensure validation passes as there are no tags to verify
            - Case B: Ensure validation passes as both tags are approved
            - Case C: Ensure validation fails as it contains a non-approved tags (NonApprovedTag)
                      Verify expected error is printed
            - Case D: Ensure validation passes as tags is approved on the same branch
            - Case E: Ensure validation fails as it contains a non-approved tag (NewTag2)
                      Verify expected error is printed
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json({
            PACK_METADATA_USE_CASES: [],
            PACK_METADATA_SUPPORT: XSOAR_SUPPORT,
            PACK_METADATA_TAGS: tags
        })
        mocker.patch.object(tools, 'is_external_repository', return_value=False)
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': branch_tags}, 'json'))
        self.validator.pack_path = pack.path

        with ChangeCWD(repo.path):
            assert self.validator._is_approved_tags() == is_valid
            if not is_valid:
                assert 'The pack metadata contains non approved tags:' in self.validator.get_errors()

    @pytest.mark.parametrize('pack_content, tags, is_valid', [
        ("none", [], True),
        ("none", ["Use Case"], False),
        ("playbook", ["Use Case"], True),
        ("incident", ["Use Case"], True),
        ("layout", ["Use Case"], True),
        ("playbook", [], True),
    ])
    def test_is_right_usage_of_usecase_tag(self, repo, pack_content, tags, is_valid):
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json({
            PACK_METADATA_USE_CASES: [],
            PACK_METADATA_SUPPORT: XSOAR_SUPPORT,
            PACK_METADATA_TAGS: tags,
        })

        if pack_content == "playbook":
            pack.create_playbook(name="PlaybookName")
        elif pack_content == "incident":
            pack.create_incident_type(name="IncidentTypeName")
        elif pack_content == "layout":
            pack.create_layout(name="Layout")

        self.validator.pack_path = pack.path

        with ChangeCWD(repo.path):
            assert self.validator.is_right_usage_of_usecase_tag() == is_valid

    @pytest.mark.parametrize('type, is_valid', [
        ('community', True),
        ('partner', True),
        ('xsoar', True),
        ('someName', False),
        ('test', False),
        ('developer', True)
    ])
    def test_is_valid_support_type(self, repo, type, is_valid):
        """
        Given:
            - Pack with support type in the metadata file.

        When:
            - Running _is_valid_support_type.

        Then:
            - Ensure True when the support types are valid, else False with the right error message.
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json({
            PACK_METADATA_USE_CASES: [],
            PACK_METADATA_SUPPORT: type
        })

        self.validator.pack_path = pack.path

        with ChangeCWD(repo.path):
            assert self.validator._is_valid_support_type() == is_valid
            if not is_valid:
                assert 'Support field should be one of the following: xsoar, partner, developer or community.' in \
                       self.validator.get_errors()

    def test_get_master_private_repo_meta_file_running_on_master(self, mocker, repo, capsys):
        """
        Given:
            - A repo which runs on master branch

        When:
            - Running get_master_private_repo_meta_file.

        Then:
            - Ensure result is None and the appropriate skipping message is printed.
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json(PACK_METADATA_PARTNER)

        class MyRepo:
            active_branch = 'master'

        mocker.patch('demisto_sdk.commands.common.hook_validations.pack_unique_files.Repo', return_value=MyRepo)
        res = self.validator.get_master_private_repo_meta_file(str(pack.pack_metadata.path))
        assert not res
        assert "Running on master branch - skipping price change validation" in capsys.readouterr().out

    def test_get_master_private_repo_meta_file_getting_git_error(self, repo, capsys, mocker):
        """
        Given:
            - A repo which runs on non-master branch.
            - git.show command raises GitCommandError.

        When:
            - Running get_master_private_repo_meta_file.

        Then:
            - Ensure result is None and the appropriate skipping message is printed.
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json(PACK_METADATA_PARTNER)

        class MyRepo:
            active_branch = 'not-master'

            class gitClass:
                def show(self, var):
                    raise GitCommandError("A", "B")

            git = gitClass()

        mocker.patch('demisto_sdk.commands.common.hook_validations.pack_unique_files.Repo', return_value=MyRepo)
        res = self.validator.get_master_private_repo_meta_file(str(pack.pack_metadata.path))
        assert not res
        assert "Got an error while trying to connect to git" in capsys.readouterr().out

    def test_get_master_private_repo_meta_file_file_not_found(self, mocker, repo, capsys):
        """
        Given:
            - A repo which runs on non-master branch.
            - git.show command returns None.

        When:
            - Running get_master_private_repo_meta_file.

        Then:
            - Ensure result is None and the appropriate skipping message is printed.
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.pack_metadata.write_json(PACK_METADATA_PARTNER)

        class MyRepo:
            active_branch = 'not-master'

            class gitClass:
                def show(self, var):
                    return None

            git = gitClass()

        mocker.patch('demisto_sdk.commands.common.hook_validations.pack_unique_files.Repo', return_value=MyRepo)
        res = self.validator.get_master_private_repo_meta_file(str(pack.pack_metadata.path))
        assert not res
        assert "Unable to find previous pack_metadata.json file - skipping price change validation" in \
               capsys.readouterr().out

    @pytest.mark.parametrize('text, result', README_INPUT_RESULTS_LIST)
    def test_validate_pack_readme_file_is_not_empty_partner(self, mocker, text, result):
        """
       Given:
            - partner pack

        When:
            - Running test_validate_pack_readme_file_is_not_empty_partner.

        Then:
            - Ensure result is False for empty README.md file and True otherwise.
        """
        self.validator = PackUniqueFilesValidator(self.FAKE_PACK_PATH)
        self.validator.support = 'partner'
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content', return_value=text)
        assert self.validator.validate_pack_readme_file_is_not_empty() == result

    @pytest.mark.parametrize('text, result', README_INPUT_RESULTS_LIST)
    def test_validate_pack_readme_file_is_not_empty_use_case(self, mocker, text, result):
        """
       Given:
            - pack with use case

        When:
            - Running test_validate_pack_readme_file_is_not_empty_partner.

        Then:
            - Ensure result is False for empty README.md file and True otherwise.
        """
        self.validator = PackUniqueFilesValidator(os.path.join(self.FILES_PATH, 'CortexXDR'))
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content', return_value=text)
        assert self.validator.validate_pack_readme_file_is_not_empty() == result

    def test_validate_pack_readme_file_is_not_empty_missing_file(self):
        self.validator = PackUniqueFilesValidator(os.path.join(self.FILES_PATH, 'DummyPack'))
        assert self.validator._is_pack_file_exists(self.validator.readme_file) is False

    def test_validate_pack_readme_valid_images(self, mocker):
        """
            Given
                - A pack README file with valid absolute image paths in it.
            When
                - Run validate on pack README file
            Then
                - Ensure:
                    - Validation succeed
                    - Valid absolute image paths were not caught
        """
        from demisto_sdk.commands.common.hook_validations.readme import \
            ReadMeValidator

        self.validator = PackUniqueFilesValidator(os.path.join(self.FILES_PATH, 'DummyPack2'))
        mocker.patch.object(ReadMeValidator, 'check_readme_relative_image_paths', return_value=[])  # Test only absolute paths

        with requests_mock.Mocker() as m:
            # Mock get requests
            m.get('https://github.com/demisto/content/raw/test1.png',
                  status_code=200, text="Test1")
            m.get('https://raw.githubusercontent.com/demisto/content/raw/test1.png',
                  status_code=200, text="Test1")
            m.get('https://raw.githubusercontent.com/demisto/content/raw/test1.jpg',
                  status_code=200, text="Test1")

            result = self.validator.validate_pack_readme_images()
            errors = self.validator.get_errors()
        assert result
        assert 'please repair it:\n![Identity with High Risk Score](https://github.com/demisto/content/raw/test1.png)'\
               not in errors
        assert 'please repair it:\n![Identity with High Risk Score](' \
               'https://raw.githubusercontent.com/demisto/content/raw/test1.png)' not in errors
        assert 'please repair it:\n(https://raw.githubusercontent.com/demisto/content/raw/test1.jpg)' not in errors

    def test_validate_pack_readme_invalid_images(self):
        """
            Given
                - A pack README file with invalid absolute and relative image paths in it.
            When
                - Run validate on pack README file
            Then
                - Ensure:
                    - Validation fails
                    - Invalid relative image paths were caught correctly
                    - Invalid absolute image paths were caught correctly
        """
        self.validator = PackUniqueFilesValidator(os.path.join(self.FILES_PATH, 'DummyPack2'))

        with requests_mock.Mocker() as m:
            # Mock get requests
            m.get('https://github.com/demisto/content/raw/test1.png',
                  status_code=404, text="Test1")
            m.get('https://raw.githubusercontent.com/demisto/content/raw/test1.png',
                  status_code=404, text="Test1")
            m.get('https://raw.githubusercontent.com/demisto/content/raw/test1.jpg',
                  status_code=404, text="Test1")

            result = self.validator.validate_pack_readme_images()
            errors = self.validator.get_errors()
        assert not result
        assert 'Detected the following image relative path: ![Identity with High Risk Score](' \
               'doc_files/High_Risk_User.png)' in errors
        assert 'Detected the following image relative path: ![Identity with High Risk Score](' \
               'home/test1/test2/doc_files/High_Risk_User.png)' in errors
        assert 'Detected the following image relative path: (../../doc_files/Access_investigation_-_Generic_4_5.png)' \
               in errors
        assert 'Image link was not found, either insert it or remove it:\n![Account Enrichment](Insert the link to ' \
               'your image here)' in errors

        assert 'please repair it:\n![Identity with High Risk Score](https://github.com/demisto/content/raw/test1.png)'\
               in errors
        assert 'please repair it:\n![Identity with High Risk Score](' \
               'https://raw.githubusercontent.com/demisto/content/raw/test1.png)' in errors
        assert 'please repair it:\n(https://raw.githubusercontent.com/demisto/content/raw/test1.jpg)' in errors

    @pytest.mark.parametrize('readme_content, is_valid', [
        ('Hey there, just testing', True),
        ('This is a test. All good!', False),
    ])
    def test_pack_readme_is_different_then_pack_description(self, repo, readme_content, is_valid):
        """
        Given:
            - Case A: A unique pack readme.
            - Case B: Pack readme that is equal to pack description

        When:
            - Validating pack readme vs pack description

        Then:
            - Case A: Ensure validation passes as the pack readme and pack description are different.
            - Case B: Ensure validation fails as the pack readme is the same as the pack description.
                      Verify expected error is printed
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        pack.readme.write_text(readme_content)
        pack.pack_metadata.write_json({
            PACK_METADATA_DESC: 'This is a test. All good!',
        })

        self.validator.pack_path = pack.path

        with ChangeCWD(repo.path):
            assert self.validator.validate_pack_readme_and_pack_description() == is_valid
            if not is_valid:
                assert 'README.md content is equal to pack description. ' \
                       'Please remove the duplicate description from README.md file' in self.validator.get_errors()

    def test_validate_pack_readme_and_pack_description_no_readme_file(self, repo):
        """
        Given:
            - A pack with no readme.

        When:
            - Validating pack readme vs pack description

        Then:
            - Fail on no README file and not on descrption error.
        """
        self.restart_validator()
        pack_name = 'PackName'
        pack = repo.create_pack(pack_name)
        self.validator.pack_path = pack.path

        with ChangeCWD(repo.path):
            os.remove(pack.readme.path)
            assert self.validator.validate_pack_readme_and_pack_description()
            assert '"README.md" file does not exist, create one in the root of the pack' in self.validator.get_errors()
            assert 'README.md content is equal to pack description. ' \
                   'Please remove the duplicate description from README.md file' not in self.validator.get_errors()

    def test_valid_is_pack_metadata_desc_too_long(self, repo):
        """
        Given:
            - Valid description length

        When:
            - Validating pack description length

        Then:
            - Ensure validation passes as the description field length is valid.

        """
        pack_description = 'Hey there, just testing'
        assert self.validator.is_pack_metadata_desc_too_long(pack_description) is True

    def test_invalid_is_pack_metadata_desc_too_long(self, mocker, repo):
        """
        Given:
            - Invalid description length - higher than 130

        When:
            - Validating pack description length

        Then:
            - Ensure validation passes although description field length is higher than 130
            - Ensure warning will be printed.
        """
        pack_description = 'This is will fail cause the description here is too long.' \
                           'test test test test test test test test test test test test test test test test test' \
                           ' test test test test test'
        error_desc = 'The description field of the pack_metadata.json file is longer than 130 characters.'

        mocker.patch("click.secho")

        assert self.validator.is_pack_metadata_desc_too_long(pack_description) is True
        assert error_desc in click.secho.call_args_list[0][0][0]

    def test_validate_author_image_exists_valid(self, repo):
        """
        Given:
            - Pack with partner support and author image

        When:
            - Validating if author image exists

        Then:
            - Ensure validation passes.
        """
        pack = repo.create_pack('MyPack')

        self.validator.metadata_content = {'support': 'partner'}
        self.validator.pack_path = pack.path
        author_image_path = pack.author_image.path

        with ChangeCWD(repo.path):
            res = self.validator.validate_author_image_exists()
            assert res
            assert f'Partners must provide a non-empty author image under the path {author_image_path}.' not in \
                   self.validator.get_errors()

    def test_validate_author_image_exists_invalid(self, repo):
        """
        Given:
            - Pack with partner support and no author image

        When:
            - Validating if author image exists

        Then:
            - Ensure validation fails.
        """
        pack = repo.create_pack('MyPack')

        self.validator.metadata_content = {'support': 'partner'}
        self.validator.pack_path = pack.path
        author_image_path = pack.author_image.path

        with ChangeCWD(repo.path):
            os.remove(author_image_path)
            res = self.validator.validate_author_image_exists()
            assert not res
            assert f'Partners must provide a non-empty author image under the path {author_image_path}.' in \
                   self.validator.get_errors()

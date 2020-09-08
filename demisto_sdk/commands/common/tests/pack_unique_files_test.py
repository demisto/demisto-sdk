import json
import os

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import PACKS_README_FILE_NAME
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator
from TestSuite.test_tools import ChangeCWD

VALIDATE_CMD = "validate"
PACK_METADATA_PARTNER_NO_EMAIL_NO_URL = {
    "name": "test",
    "description": "test",
    "support": "partner",
    "currentVersion": "1.0.1",
    "author": "bar",
    "url": '',
    "email": '',
    "created": "2020-03-12T08:00:00Z",
    "categories": [
        "Data Enrichment & Threat Intelligence"
    ],
    "tags": [],
    "useCases": [],
    "keywords": []
}


class TestPackUniqueFilesValidator:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
    FAKE_PACK_PATH = os.path.join(FILES_PATH, 'fake_pack')
    FAKE_PATH_NAME = 'fake_pack'
    validator = PackUniqueFilesValidator(FAKE_PATH_NAME)
    validator.pack_path = FAKE_PACK_PATH

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
        assert not self.validator.validate_pack_unique_files()
        fake_validator = PackUniqueFilesValidator('fake')
        assert fake_validator.validate_pack_unique_files()

    def test_validate_pack_metadata(self, mocker):
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        assert not self.validator.validate_pack_unique_files()
        fake_validator = PackUniqueFilesValidator('fake')
        assert fake_validator.validate_pack_unique_files()

    def test_validate_partner_contribute_pack_metadata(self, mocker, repo):
        """
        Given
        - Partner contributed pack without email and url.

        When
        - Running validate on it.

        Then
        - Ensure validate found errors.
        """
        mocker.patch.object(tools, 'is_external_repository', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=json.dumps(PACK_METADATA_PARTNER_NO_EMAIL_NO_URL))
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value=None)
        pack = repo.create_pack('PackName')
        pack.pack_metadata.write_json(PACK_METADATA_PARTNER_NO_EMAIL_NO_URL)
        with ChangeCWD(repo.path):
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [VALIDATE_CMD, '-i', pack.path], catch_exceptions=False)
        assert 'Contributed packs must include email or url' in result.stdout

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

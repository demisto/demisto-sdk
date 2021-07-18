import io
import os

import pytest
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator, CONTRIBUTORS_LIST, PACK_METADATA_NAME, PACK_METADATA_SUPPORT
from demisto_sdk.commands.common.legacy_git_tools import git_path
from typing import Dict


class TestPackMetadataValidator:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))

    @pytest.mark.parametrize('metadata', [os.path.join(FILES_PATH, 'pack_metadata__valid.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata__valid__community.json'),
                                          ])
    def test_metadata_validator_valid(self, mocker, metadata):
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=TestPackMetadataValidator.read_file(metadata))
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)

        validator = PackUniqueFilesValidator('fake')
        assert validator.validate_pack_meta_file()

    # TODO: add the validation for price after #23546 is ready.
    @pytest.mark.parametrize('metadata', [os.path.join(FILES_PATH, 'pack_metadata_missing_fields.json'),
                                          # os.path.join(FILES_PATH, 'pack_metadata_invalid_price.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_invalid_dependencies.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_list_dependencies.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_empty_category.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_invalid_keywords.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_invalid_tags.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_list.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_short_name.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_name_start_lower.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_name_start_incorrect.json'),
                                          os.path.join(FILES_PATH, 'pack_metadata_pack_in_name.json'),
                                          ])
    def test_metadata_validator_invalid(self, mocker, metadata):
        mocker.patch.object(tools, 'get_dict_from_file', return_value=({'approved_list': []}, 'json'))
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=TestPackMetadataValidator.read_file(metadata))
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)
        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')

        validator = PackUniqueFilesValidator('fake')
        assert not validator.validate_pack_meta_file()

    VALIDATE_PACK_NAME_INPUTS = [({PACK_METADATA_NAME: 'fill mandatory field'}, False),
                                 ({PACK_METADATA_NAME: 'A'}, False),
                                 ({PACK_METADATA_NAME: 'notCapitalized'}, False),
                                 ({PACK_METADATA_NAME: 'BitcoinAbuse (Community)', PACK_METADATA_SUPPORT: 'community'},
                                  False),
                                 ({PACK_METADATA_NAME: 'BitcoinAbuse'}, True)]

    @pytest.mark.parametrize('metadata_content, expected', VALIDATE_PACK_NAME_INPUTS)
    def test_validate_pack_name(self, metadata_content: Dict, expected: bool, mocker):
        """
        Given:
        - Metadata JSON pack file content.

        When:
        - Validating if pack name is valid.

        Then:
        - Ensure expected result is returned.
        """
        validator = PackUniqueFilesValidator('fake')
        mocker.patch.object(validator, '_add_error', return_value=True)
        assert validator.validate_pack_name(metadata_content) == expected

    @staticmethod
    def read_file(file_):
        with io.open(file_, mode="r", encoding="utf-8") as data:
            return data.read()

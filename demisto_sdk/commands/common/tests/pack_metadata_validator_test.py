import io
import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator


class TestPackMetadataValidator:
    FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))

    def test_metadata_validator_valid(self, mocker):
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=TestPackMetadataValidator.
                            read_file(os.path.join(TestPackMetadataValidator.FILES_PATH,
                                                   'valid_pack_metadata.json')))
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
                                          os.path.join(FILES_PATH, 'pack_metadata_list.json')
                                          ])
    def test_metadata_validator_invalid(self, mocker, metadata):
        mocker.patch.object(PackUniqueFilesValidator, '_read_file_content',
                            return_value=TestPackMetadataValidator.read_file(metadata))
        mocker.patch.object(PackUniqueFilesValidator, '_is_pack_file_exists', return_value=True)

        validator = PackUniqueFilesValidator('fake')
        assert not validator.validate_pack_meta_file()

    @staticmethod
    def read_file(file_):
        with io.open(file_, mode="r", encoding="utf-8") as data:
            return data.read()

from demisto_sdk.commands.common.legacy_git_tools import git_path
import pytest
from demisto_sdk.commands.convert.convert_manager import ConvertManager
from packaging.version import Version

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'
PACK_TEST_DIR = f'{git_path()}/demisto_sdk/commands/convert/tests/test_data/Packs/ExtraHop'


class TestConvertManager:
    TEST_CREATE_PACK_OBJECT_INPUTS = [(PACK_TEST_DIR, PACK_TEST_DIR), (f'{PACK_TEST_DIR}/Layouts', PACK_TEST_DIR)]

    @pytest.mark.parametrize('dir_path, expected_pack_path', TEST_CREATE_PACK_OBJECT_INPUTS)
    def test_create_pack_object(self, dir_path: str, expected_pack_path: str):
        convert_manager = ConvertManager(dir_path, '6.0.0')
        pack_obj = convert_manager.create_pack_object()
        assert str(pack_obj.path) == expected_pack_path

    TEST_SERVER_VERSION_IS_NOT_SUPPORTED_INPUTS = [(str(ConvertManager.SERVER_MIN_VERSION_SUPPORTED), True),
                                                   (str(ConvertManager.SERVER_MAX_VERSION_SUPPORTED), True),
                                                   ('5.4.0', False),
                                                   ('9.0.0', False)]

    @pytest.mark.parametrize('server_version, expected', TEST_SERVER_VERSION_IS_NOT_SUPPORTED_INPUTS)
    def test_server_version_not_supported(self, server_version: str, expected: bool):
        convert_manager = ConvertManager(input_path='', server_version=server_version)
        assert convert_manager.server_version_not_supported() == expected

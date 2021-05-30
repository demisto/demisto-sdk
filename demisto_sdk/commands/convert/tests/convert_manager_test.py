import pytest
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.convert_manager import ConvertManager

TESTS_DIR = f'{git_path()}/demisto_sdk/tests'
PACK_TEST_DIR = f'{git_path()}/demisto_sdk/commands/convert/tests/test_data/Packs/ExtraHop'


class TestConvertManager:
    TEST_CREATE_PACK_OBJECT_INPUTS = [(PACK_TEST_DIR, PACK_TEST_DIR), (f'{PACK_TEST_DIR}/Layouts', PACK_TEST_DIR)]

    @pytest.mark.parametrize('dir_path, expected_pack_path', TEST_CREATE_PACK_OBJECT_INPUTS)
    def test_create_pack_object(self, dir_path: str, expected_pack_path: str):
        """
        Given:
        - directory path from the -i argument in convert command.

        When:
        - Wanting to create the Pack object of the corresponding pack that can be found in the input path.

        Then:
        - Ensure expected Pack object is returned.

        """
        convert_manager = ConvertManager(dir_path, '6.0.0')
        pack_obj = convert_manager.create_pack_object()
        assert str(pack_obj.path) == expected_pack_path

    TEST_SERVER_VERSION_IS_NOT_SUPPORTED_INPUTS = [(str(ConvertManager.SERVER_MIN_VERSION_SUPPORTED), True),
                                                   (str(ConvertManager.SERVER_MAX_VERSION_SUPPORTED), True),
                                                   ('5.4.0', False),
                                                   ('9.0.0', False)]

    @pytest.mark.parametrize('server_version, expected', TEST_SERVER_VERSION_IS_NOT_SUPPORTED_INPUTS)
    def test_server_version_not_supported(self, server_version: str, expected: bool):
        """
        Given:
        - ConvertManager with its initialized server version, given by -v argument in convert command.

        When:
        - Checking if given version is supported by convert command.

        Then:
        - Ensure expected boolean is returned indicating whether version is supported or not.
        """
        convert_manager = ConvertManager(input_path='', server_version=server_version)
        assert convert_manager.server_version_not_supported() == expected

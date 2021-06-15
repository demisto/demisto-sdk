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

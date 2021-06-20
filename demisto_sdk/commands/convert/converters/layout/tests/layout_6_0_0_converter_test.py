import io
import json
import os
from pathlib import Path

import pytest
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.layout.layout_6_0_0_converter import \
    LayoutSixConverter
from TestSuite.pack import Pack as MockPack
from TestSuite.repo import Repo


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestLayoutSixConverter:
    LAYOUT_CLOSE_PATH = os.path.join(__file__,
                                     f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                     '/test_data/layout-close-ExtraHop_Detection.json')
    LAYOUT_DETAILS_PATH = os.path.join(__file__,
                                       f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                       '/test_data/layout-details-ExtraHop_Detection.json')
    LAYOUT_EDIT_PATH = os.path.join(__file__,
                                    f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                    '/test_data/layout-edit-ExtraHop_Detection.json')
    LAYOUT_QUICK_VIEW_PATH = os.path.join(__file__,
                                          f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                          '/test_data/layout-quickView-ExtraHop_Detection.json')
    LAYOUT_MOBILE_PATH = os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                                '/test_data/layout-mobile-ExtraHop_Detection.json')

    def test_get_layout_indicator_fields(self, tmpdir):
        """
        Given:
        - Schema path of the layouts-container.

        When:
        - Wanting to retrieve all indicator dynamic fields in the schema.

        Then:
        - Ensure indicator dynamic fields are returned.
        """
        layout_converter = LayoutSixConverter(Pack(tmpdir))
        dynamic_fields = set(layout_converter.get_layout_indicator_fields())
        assert dynamic_fields == {'indicatorsDetails', 'indicatorsQuickView'}

    def test_group_layouts_needing_conversion_by_layout_id(self, tmpdir):
        """
        Given:
        -

        When:
        - Grouping layouts needing conversion by their layout ID.

        Then:
        - Ensure expected dict object is returned.
        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_layout('close-ExtraHop_Detection', util_load_json(self.LAYOUT_CLOSE_PATH))
        fake_pack.create_layout('details-ExtraHop_Detection', util_load_json(self.LAYOUT_DETAILS_PATH))
        fake_pack.create_layout('edit-ExtraHop_Detection', util_load_json(self.LAYOUT_EDIT_PATH))
        fake_pack.create_layout('quickView-ExtraHop_Detection',
                                util_load_json(self.LAYOUT_QUICK_VIEW_PATH))
        fake_pack.create_layout('mobile-ExtraHop_Detection', util_load_json(self.LAYOUT_MOBILE_PATH))
        fake_pack_path = fake_pack.path
        layout_converter = LayoutSixConverter(Pack(fake_pack_path))
        result = layout_converter.group_layouts_needing_conversion_by_layout_id()
        assert len(result) == 1 and 'ExtraHop Detection' in result
        layout_kinds = {layout['kind'] for layout in result['ExtraHop Detection']}
        assert all(layout.layout_id() == 'ExtraHop Detection' for layout in result['ExtraHop Detection'])
        assert layout_kinds == {'close', 'details', 'edit', 'mobile', 'quickView'}

    CALCULATE_NEW_LAYOUT_GROUP_INPUTS = [(os.path.join(__file__,
                                                       f'{git_path()}/demisto_sdk/commands/convert/converters/layout/'
                                                       'tests/test_data/layout-mobile-ExtraHop_Detection.json'),
                                          'incident'),
                                         (os.path.join(__file__,
                                                       f'{git_path()}/demisto_sdk/commands/convert/converters/'
                                                       'layout/tests/test_data/layout-indicatorsDetails-Crypto'
                                                       'currency_Address-V3.json'), 'indicator')]

    @pytest.mark.parametrize('old_layout_path, expected', CALCULATE_NEW_LAYOUT_GROUP_INPUTS)
    def test_calculate_new_layout_group(self, tmpdir, old_layout_path: str, expected: str):
        """
        Given:
        - 'old_layouts': List of old layout objects.

        When:
        - Calculating the group field value for the layout above 6.0.0 version to be created.

        Then:
        - Ensure the expected group value is returned.
        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_layout('test', util_load_json(old_layout_path))
        fake_pack_path = fake_pack.path
        layout_converter = LayoutSixConverter(Pack(fake_pack_path))
        assert layout_converter.calculate_new_layout_group(
            [layout for layout in layout_converter.pack.layouts]) == expected

    CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS = [('ExtraHop Detection', 'layoutscontainer-ExtraHop_Detection.json')]

    @pytest.mark.parametrize('layout_id, expected_suffix',
                             CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS)
    def test_calculate_new_layout_relative_path(self, tmpdir, layout_id: str, expected_suffix: str):
        """
        Given:
        - 'layout_id': Layout ID of the new layout created.

        When:
        - Calculating the path to the newly created layout.

        Then:
        - Ensure the expected path is returned.

        """
        layout_converter = LayoutSixConverter(Pack(tmpdir))
        expected = f'{layout_converter.pack.path}/Layouts/{expected_suffix}'
        assert layout_converter.calculate_new_layout_relative_path(layout_id) == expected

    def test_convert_dir(self, tmpdir):
        """
        Given:
        - Pack.

        When:
        - Converting every layout of version 6.0.0 and above to version 5.9.9 and below.

        Then:
        - Ensure expected layouts are created with expected values.
        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_layout('close-ExtraHop_Detection', util_load_json(self.LAYOUT_CLOSE_PATH))
        fake_pack.create_layout('details-ExtraHop_Detection', util_load_json(self.LAYOUT_DETAILS_PATH))
        fake_pack.create_layout('edit-ExtraHop_Detection', util_load_json(self.LAYOUT_EDIT_PATH))
        fake_pack.create_layout('quickView-ExtraHop_Detection',
                                util_load_json(self.LAYOUT_QUICK_VIEW_PATH))
        fake_pack.create_layout('mobile-ExtraHop_Detection', util_load_json(self.LAYOUT_MOBILE_PATH))
        fake_pack_path = fake_pack.path
        layout_converter = LayoutSixConverter(Pack(fake_pack_path))
        layout_converter.convert_dir()
        expected_new_layout_path = f'{str(layout_converter.pack.path)}/Layouts/layoutscontainer-ExtraHop_Detection.json'
        assert os.path.exists(expected_new_layout_path)
        with open(expected_new_layout_path, 'r') as f:
            layout_data = json.loads(f.read())
        test_data_json = util_load_json(os.path.join(__file__,
                                                     f'{git_path()}/demisto_sdk/commands/convert/converters/layout/'
                                                     'tests/test_data'
                                                     '/layoutscontainer-ExtraHop_Detection.json'))
        assert layout_data == test_data_json
        os.remove(expected_new_layout_path)

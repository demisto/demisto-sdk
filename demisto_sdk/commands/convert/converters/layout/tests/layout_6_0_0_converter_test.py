import io
import json
import os
from typing import List

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import (
    Layout, LayoutObject)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.layout.layout_6_0_0_converter import \
    LayoutSixConverter


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestLayoutSixConverter:
    TEST_PACK_PATH = os.path.join(__file__,
                                  f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data/Packs'
                                  '/ExtraHop')
    PACK_WITH_OLD_LAYOUTS_PATH = os.path.join(__file__,
                                              f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                              '/test_data/Packs'
                                              '/PackWithOldLayout')
    SCHEMA_PATH = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data',
                     'layoutscontainer.yml'))

    def setup(self):
        self.layout_converter = LayoutSixConverter(Pack(self.TEST_PACK_PATH))

    def test_get_layout_indicator_fields(self):
        """
        Given:
        - Schema path of the layouts-container.

        When:
        - Wanting to retrieve all indicator dynamic fields in the schema.

        Then:
        - Ensure indicator dynamic fields are returned.
        """
        dynamic_fields = set(self.layout_converter.get_layout_indicator_fields(self.SCHEMA_PATH))
        assert dynamic_fields == {'indicatorsDetails', 'indicatorsQuickView'}

    def test_group_layouts_needing_conversion_by_layout_id(self):
        """
        Given:
        -

        When:
        - Grouping layouts needing conversion by their layout ID.

        Then:
        - Ensure expected dict object is returned.
        """
        result = self.layout_converter.group_layouts_needing_conversion_by_layout_id()
        assert len(result) == 1 and 'ExtraHop Detection' in result
        layout_kinds = {layout['kind'] for layout in result['ExtraHop Detection']}
        assert all(layout.layout_id() == 'ExtraHop Detection' for layout in result['ExtraHop Detection'])
        assert layout_kinds == {'close', 'details', 'edit', 'mobile', 'quickView'}

    CALCULATE_NEW_LAYOUT_GROUP_INPUTS = [([], 'incident'),
                                         ([Layout(os.path.join(__file__,
                                                               f'{git_path()}/demisto_sdk/commands/convert/converters/'
                                                               f'layout/tests/test_data/Packs/ExtraHop/Layouts/'
                                                               f'layout-mobile-ExtraHop_Detection.json'))], 'incident'),
                                         ([Layout(os.path.join(__file__,
                                                               f'{git_path()}/demisto_sdk/commands/convert/converters/'
                                                               f'layout/tests/test_data/layout-indicatorsDetails-Crypto'
                                                               f'currency_Address-V3.json'))], 'indicator')]

    @pytest.mark.parametrize('old_layouts, expected', CALCULATE_NEW_LAYOUT_GROUP_INPUTS)
    def test_calculate_new_layout_group(self, old_layouts: List[LayoutObject], expected: str):
        """
        Given:
        - 'old_layouts': List of old layout objects.

        When:
        - Calculating the group field value for the layout above 6.0.0 version to be created.

        Then:
        - Ensure the expected group value is returned.
        """
        assert self.layout_converter.calculate_new_layout_group(old_layouts) == expected

    CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS = [('ExtraHop Detection', 'layoutscontainer-ExtraHop_Detection.json')]

    @pytest.mark.parametrize('layout_id, expected_suffix',
                             CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS)
    def test_calculate_new_layout_relative_path(self, layout_id: str, expected_suffix: str):
        """
        Given:
        - 'layout_id': Layout ID of the new layout created.

        When:
        - Calculating the path to the newly created layout.

        Then:
        - Ensure the expected path is returned.

        """
        expected = f'{self.layout_converter.pack.path}/Layouts/{expected_suffix}'
        assert self.layout_converter.calculate_new_layout_relative_path(layout_id) == expected

    def test_convert_dir(self):
        # TODO docs
        layout_converter = LayoutSixConverter(Pack(self.PACK_WITH_OLD_LAYOUTS_PATH))
        layout_converter.convert_dir()
        expected_new_layout_path = f'{self.PACK_WITH_OLD_LAYOUTS_PATH}/Layouts/layoutscontainer-ExtraHop_Detection.json'
        assert os.path.exists(expected_new_layout_path)
        with open(expected_new_layout_path, 'r') as f:
            layout_data = json.loads(f.read())
        assert layout_data == util_load_json('test_data/layout_6_0_0_expected_convert_dir_test_file_output.json')
        os.remove(expected_new_layout_path)

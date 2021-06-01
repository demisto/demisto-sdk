import io
import json
import os
from typing import Dict, List

import pytest
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import (
    Layout, LayoutObject)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.layout.layout_up_to_5_9_9_converter import \
    LayoutBelowSixConverter


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestLayoutBelowSixConverter:
    TEST_PACK_PATH = os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/tests/test_data/Packs/ExtraHop')
    PACK_WITH_NEW_LAYOUTS_PATH = os.path.join(__file__,
                                              f'{git_path()}/demisto_sdk/commands/convert/converters/layout/'
                                              'tests/test_data/Packs/PackWithNewLayout')
    PACK = Pack(TEST_PACK_PATH)

    def setup(self):
        self.layout_converter = LayoutBelowSixConverter(TestLayoutBelowSixConverter.PACK)

    CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS = [('ExtraHop Detect', 'close', 'layout-close-ExtraHop_Detect.json')]

    @pytest.mark.parametrize('dynamic_field_key, type_id, expected_suffix',
                             CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS)
    def test_calculate_new_layout_relative_path(self, dynamic_field_key: str, type_id: str, expected_suffix: str):
        """
        Given:
        - 'layout_id': Layout ID of the new layout created.
        - 'dynamic_key_field': The dynamic key field related to the new layout created until version 5.9.9.
        - 'type_id': Type ID of the corresponding incident/indicator

        When:
        - Calculating the path to the newly created layout.

        Then:
        - Ensure the expected path is returned.

        """
        expected = f'{self.layout_converter.pack.path}/Layouts/{expected_suffix}'
        assert self.layout_converter.calculate_new_layout_relative_path(type_id, dynamic_field_key) == expected

    def test_layout_to_incidents_dict(self):
        """
        Given:
        - Incident types of the pack.

        When:
        - Creating a dict of key as layout ID and value as list of incident type IDs whom layout field equals to layout
          ID.

        Then:
        - Ensure expected dict is returned.

        """
        result = self.layout_converter.layout_to_indicators_or_incidents_dict(self.layout_converter.pack.incident_types)
        assert result == {'ExtraHop Detection': ['ExtraHop Detection', 'ExtraHop Detection 2']}

    def test_layout_to_indicators_dict(self):
        """
        Given:
        - Indicator types of the pack.

        When:
        - Creating a dict of key as layout ID and value as list of indicator type IDs whom layout field equals to layout
          ID.

        Then:
        - Ensure expected dict is returned.

        """
        res = self.layout_converter.layout_to_indicators_or_incidents_dict(self.layout_converter.pack.indicator_types)
        assert res == {'ExtraHop Detection': ['Cryptocurrency Address']}

    BUILD_OLD_LAYOUT_INPUTS = [('ExtraHop Detection', 'ExtraHop Detect', 'close', None,
                                {'fromVersion': '4.1.0',
                                 'kind': 'close',
                                 'layout': {
                                     'id': 'ExtraHop Detection',
                                     'kind': 'close',
                                     'name': 'ExtraHop Detection',
                                     'typeId': 'ExtraHop Detect',
                                     'version': -1},
                                 'toVersion': '5.9.9',
                                 'typeId': 'ExtraHop Detect',
                                 'version': -1}),
                               ('ExtraHop Detection', 'ExtraHop Detect', 'mobile', None,
                                {'fromVersion': '4.1.0',
                                 'kind': 'mobile',
                                 'layout': {
                                     'id': 'ExtraHop Detection',
                                     'kind': 'mobile',
                                     'name': 'ExtraHop Detection',
                                     'typeId': 'ExtraHop Detect',
                                     'version': -1},
                                 'toVersion': '5.9.9',
                                 'typeId': 'ExtraHop Detect',
                                 'version': -1}),
                               ('ExtraHop Detection', 'ExtraHop Detect', 'close', {'a': 'b'},
                                {'fromVersion': '4.1.0',
                                 'kind': 'close',
                                 'layout': {
                                     'id': 'ExtraHop Detection',
                                     'kind': 'close',
                                     'name': 'ExtraHop Detection',
                                     'typeId': 'ExtraHop Detect',
                                     'version': -1,
                                     'a': 'b'},
                                 'toVersion': '5.9.9',
                                 'typeId': 'ExtraHop Detect',
                                 'version': -1}),
                               ]

    @pytest.mark.parametrize('layout_id, incident_type_id, dynamic_field_key, dynamic_field_value, expected',
                             BUILD_OLD_LAYOUT_INPUTS)
    def test_build_old_layout(self, layout_id: str, incident_type_id: str, dynamic_field_key: str,
                              dynamic_field_value: str, expected: Dict):
        """
        Given:
        - 'layout_id': Old layout ID to be created.
        - 'incident_type_id': Incident type ID corresponding to the newly created old layout.
        - 'dynamic_field_key': The dynamic field key from whom the layout will be created.
        - 'dynamic_field_value': The dynamic field value from whom the layout will be created.

        When:
        - Creating layout of the format below 6.0.0 version.

        Then:
        - Ensure expected dict is returned.

        """
        assert self.layout_converter.build_old_layout(layout_id, incident_type_id, dynamic_field_key,
                                                      dynamic_field_value, from_version='4.1.0') == expected

    def test_convert_dir(self):
        """
        Given:
        - Pack.

        When:
        - Converting every layout of version 6.0.0 and above to version 5.9.9 and below.

        Then:
        - Ensure expected layouts are created with expected values.
        """
        layout_converter = LayoutBelowSixConverter(Pack(self.PACK_WITH_NEW_LAYOUTS_PATH))
        layout_converter.convert_dir()
        test_data_json = util_load_json(os.path.join(__file__,
                                                     f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                                     '/test_data'
                                                     '/layout_up_to_5_9_9_expected_convert_dir_test_file_output.json'))
        for layout_field_name, layout_data in test_data_json.items():
            expected_new_layout_path = f'{self.PACK_WITH_NEW_LAYOUTS_PATH}/Layouts/layout-{layout_field_name}-' \
                                       'ExtraHop_Detection.json'
            assert os.path.exists(expected_new_layout_path)
            assert util_load_json(expected_new_layout_path) == layout_data
            os.remove(expected_new_layout_path)

    OLD_LAYOUT_PATH = os.path.join(__file__,
                                   f'{git_path()}/demisto_sdk/commands/convert/tests/test_data/Packs'
                                   '/PackWithOldLayout/Layouts/layout-close-ExtraHop_Detection.json')
    CALCULATE_FROM_VERSION_INPUTS = [('ExtraHop Detection', 'close', [Layout(OLD_LAYOUT_PATH)], '5.0.0'),
                                     ('ExtraHop Detection2', 'close', [Layout(OLD_LAYOUT_PATH)], '4.1.0'),
                                     ('ExtraHop Detection', 'mobile', [Layout(OLD_LAYOUT_PATH)], '4.1.0')]

    @pytest.mark.parametrize('layout_id, layout_kind, current_old_layouts, expected', CALCULATE_FROM_VERSION_INPUTS)
    def test_calculate_from_version(self, layout_id: str, layout_kind: str, current_old_layouts: List[LayoutObject],
                                    expected: str):
        """
        Given:
        - 'layout_id' Layout ID.
        - 'layout_kind' Layout kind.
        - 'current_old_layouts': Old layouts existing in the Layouts directory before the conversion.

        When:
        - Calculating the from version for the new layout to be created.

        Then:
        - Ensure that from version from existing layout is returned if corresponding layout exists with from version,
          else 'MINIMAL_FROM_VERSION' is returned.
        """
        assert self.layout_converter.calculate_from_version(layout_id, layout_kind, current_old_layouts) == expected

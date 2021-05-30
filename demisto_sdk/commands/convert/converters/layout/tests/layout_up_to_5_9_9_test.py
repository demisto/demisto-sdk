import io
import json
import os
from typing import Dict

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.layout.layout_up_to_5_9_9_converter import LayoutBelowSixConverter


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestLayoutBelowSixConverter:
    TEST_PACK_PATH = os.path.join(__file__,
                                  f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data/Packs'
                                  f'/ExtraHop')
    PACK_WITH_NEW_LAYOUTS_PATH = os.path.join(__file__,
                                              f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                              '/test_data/Packs'
                                              '/PackWithNewLayout')

    def setup(self):
        self.layout_converter = LayoutBelowSixConverter(Pack(self.TEST_PACK_PATH))

    CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS = [('ExtraHop Detection', 'close', 'ExtraHop Detection',
                                                  'layout-close-ExtraHop_Detection.json')]

    @pytest.mark.parametrize('layout_id, dynamic_field_key, incident_type_id, expected_suffix',
                             CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS)
    def test_calculate_new_layout_relative_path(self, layout_id: str, dynamic_field_key: str, incident_type_id: str,
                                                expected_suffix: str):
        """
        Given:
        - 'layout_id': Layout ID of the new layout created.
        - 'dynamic_key_field': The dynamic key field related to the new layout created until version 5.9.9.
        - 'incident_type_id': TODO: delete or explain

        When:
        - Calculating the path to the newly created layout.

        Then:
        - Ensure the expected path is returned.

        """
        expected = f'{self.layout_converter.pack.path}/Layouts/{expected_suffix}'
        assert self.layout_converter.calculate_new_layout_relative_path(layout_id, dynamic_field_key,
                                                                        incident_type_id) == expected

    def test_create_layout_id_to_incident_types_id_dict(self):
        """
        Given:
        -

        When:
        - Creating a dict of key as layout ID and value as list of incident type IDs whom layout field equals to layout
          ID.

        Then:
        - Ensure expected dict is returned.

        """
        assert self.layout_converter.create_layout_id_to_incident_types_id_dict() == {
            'ExtraHop Detection': ['ExtraHop Detection', 'ExtraHop Detection 2']}

    BUILD_OLD_LAYOUT_INPUTS = [('ExtraHop Detection', 'ExtraHop Detect', 'close', None,
                                {'fromVersion': '4.1.0',
                                 'kind': 'close',
                                 'layouts': {
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
                                 'layouts': {
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
                                 'layouts': {
                                     'id': 'ExtraHop Detection',
                                     'kind': 'close',
                                     'name': 'ExtraHop Detection',
                                     'typeId': 'ExtraHop Detect',
                                     'version': -1},
                                 'toVersion': '5.9.9',
                                 'typeId': 'ExtraHop Detect',
                                 'version': -1,
                                 'a': 'b'}),
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
                                                      dynamic_field_value) == expected

    def test_convert_dir(self):
        layout_converter = LayoutBelowSixConverter(Pack(self.PACK_WITH_NEW_LAYOUTS_PATH))
        layout_converter.convert_dir()
        test_data_json = util_load_json('test_data/layout_up_to_5_9_9_expected_convert_dir_test_file_output.json')
        for layout_field_name, layout_data in test_data_json.items():
            expected_new_layout_path = f'{self.PACK_WITH_NEW_LAYOUTS_PATH}/Layouts/layout-{layout_field_name}-' \
                                       'ExtraHop_Detection.json'
            assert os.path.exists(expected_new_layout_path)
            assert util_load_json(expected_new_layout_path) == layout_data
            os.remove(expected_new_layout_path)

import io
import json
import os
from pathlib import Path
from typing import Dict

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import \
    Layout
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.layout.layout_up_to_5_9_9_converter import \
    LayoutBelowSixConverter
from TestSuite.pack import Pack as MockPack
from TestSuite.repo import Repo


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestLayoutBelowSixConverter:
    INCIDENT_TYPE_ONE = os.path.join(__file__,
                                     f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                     '/test_data/incidenttype-ExtraHop_Detection.json')
    INCIDENT_TYPE_TWO = os.path.join(__file__,
                                     f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                     '/test_data/incidenttype-ExtraHop_Detection_2.json')
    INDICATOR_TYPE_ONE = os.path.join(__file__,
                                      f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                      '/test_data/reputation-cryptocurrency.json')
    LAYOUT_CONTAINER = os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                              '/test_data/layoutscontainer-ExtraHop_Detection.json')
    OLD_LAYOUT_PATH = os.path.join(__file__,
                                   f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data'
                                   '/layout-close-ExtraHop_Detection.json')

    CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS = [('ExtraHop Detect', 'close', 'layout-close-ExtraHop_Detect.json')]

    @pytest.mark.parametrize('dynamic_field_key, type_id, expected_suffix',
                             CALCULATE_NEW_LAYOUT_RELATIVE_PATH_INPUTS)
    def test_calculate_new_layout_relative_path(self, tmpdir, dynamic_field_key: str, type_id: str,
                                                expected_suffix: str):
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
        layout_converter = LayoutBelowSixConverter(Pack(tmpdir))
        expected = f'{layout_converter.pack.path}/Layouts/{expected_suffix}'
        assert layout_converter.calculate_new_layout_relative_path(type_id, dynamic_field_key) == expected

    def test_layout_to_incidents_dict(self, tmpdir):
        """
        Given:
        - Incident types of the pack.

        When:
        - Creating a dict of key as layout ID and value as list of incident type IDs whom layout field equals to layout
          ID.

        Then:
        - Ensure expected dict is returned.

        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_incident_type('ExtraHop_Detection', util_load_json(self.INCIDENT_TYPE_ONE))
        fake_pack.create_incident_type('ExtraHop_Detection_2', util_load_json(self.INCIDENT_TYPE_TWO))
        fake_pack_path = fake_pack.path
        layout_converter = LayoutBelowSixConverter(Pack(fake_pack_path))
        result = LayoutBelowSixConverter.layout_to_indicators_or_incidents_dict(layout_converter.pack.incident_types)
        assert result == {'ExtraHop Detection': ['ExtraHop Detection', 'ExtraHop Detection 2']}

    def test_layout_to_indicators_dict(self, tmpdir):
        """
        Given:
        - Indicator types of the pack.

        When:
        - Creating a dict of key as layout ID and value as list of indicator type IDs whom layout field equals to layout
          ID.

        Then:
        - Ensure expected dict is returned.

        """
        fake_pack_name = 'FakeTestPack'
        repo = Repo(tmpdir)
        repo_path = Path(repo.path)
        fake_pack = MockPack(repo_path / 'Packs', fake_pack_name, repo)
        fake_pack.create_indicator_type('Cryptocurrency Address', util_load_json(self.INDICATOR_TYPE_ONE))
        fake_pack_path = fake_pack.path
        layout_converter = LayoutBelowSixConverter(Pack(fake_pack_path))
        res = layout_converter.layout_to_indicators_or_incidents_dict(layout_converter.pack.indicator_types)
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
    def test_build_old_layout(self, tmpdir, layout_id: str, incident_type_id: str, dynamic_field_key: str,
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
        assert LayoutBelowSixConverter(Pack(tmpdir)).build_old_layout(layout_id, incident_type_id, dynamic_field_key,
                                                                      dynamic_field_value,
                                                                      from_version='4.1.0') == expected

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
        fake_pack.create_incident_type('ExtraHop_Detection', util_load_json(self.INCIDENT_TYPE_ONE))
        fake_pack.create_layoutcontainer('ExtraHop Detection', util_load_json(self.LAYOUT_CONTAINER))
        fake_pack_path = fake_pack.path
        layout_converter = LayoutBelowSixConverter(Pack(fake_pack_path))
        layout_converter.convert_dir()
        test_data_json = util_load_json(os.path.join(__file__,
                                                     f'{git_path()}/demisto_sdk/commands/convert/converters/layout/'
                                                     'tests/test_data'
                                                     '/layout_up_to_5_9_9_expected_convert_dir_test_file_output.json'))
        for layout_field_name, layout_data in test_data_json.items():
            expected_new_layout_path = f'{str(layout_converter.pack.path)}/Layouts/layout-{layout_field_name}-' \
                                       'ExtraHop_Detection.json'
            assert os.path.exists(expected_new_layout_path)
            assert util_load_json(expected_new_layout_path) == layout_data
            os.remove(expected_new_layout_path)

    CALCULATE_FROM_VERSION_INPUTS = [('ExtraHop Detection', 'close', '5.5.0'),
                                     ('ExtraHop Detection2', 'close', '5.0.0'),
                                     ('ExtraHop Detection', 'mobile', '5.0.0')]

    @pytest.mark.parametrize('layout_id, layout_kind, expected', CALCULATE_FROM_VERSION_INPUTS)
    def test_calculate_from_version(self, tmpdir, layout_id: str, layout_kind: str, expected: str):
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
        full_layout_path = os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/'
                                                  'test_data/layout-close-ExtraHop_Detection.json')
        assert LayoutBelowSixConverter(Pack(tmpdir)).calculate_from_version(layout_id, layout_kind,
                                                                            [Layout(full_layout_path)]) == expected

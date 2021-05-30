import io
import json
import os
from typing import Dict

import pytest

from demisto_sdk.commands.common.constants import FileType, ENTITY_NAME_SEPARATORS
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.layout.layout_base_converter import LayoutBaseConverter


def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())


class TestLayoutBaseConverter:
    TEST_PACK_PATH = os.path.join(__file__,
                                  f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data/Packs'
                                  f'/ExtraHop')
    SCHEMA_PATH = os.path.normpath(
        os.path.join(__file__, f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data',
                     'layoutscontainer.yml'))

    def setup(self):
        self.layout_converter = LayoutBaseConverter(Pack(self.TEST_PACK_PATH))

    CREATE_LAYOUT_DICT_INPUTS = [(dict(), {'version': -1}),
                                 ({'from_version': '4.1.0', 'to_version': '5.9.9', 'kind': 'quickView',
                                   'type_id': 'ExtraHop Incident'},
                                  {'fromVersion': '4.1.0', 'toVersion': '5.9.9', 'version': -1, 'kind': 'quickView',
                                   'typeId': 'ExtraHop Incident'}),
                                 ({'from_version': '6.0.0', 'layout_id': 'ExtraHop Incident'},
                                  {'fromVersion': '6.0.0', 'name': 'ExtraHop Incident', 'id': 'ExtraHop Incident',
                                   'version': -1})]

    @pytest.mark.parametrize('inputs, expected', CREATE_LAYOUT_DICT_INPUTS)
    def test_create_layout_dict(self, inputs: Dict, expected: Dict):
        """
        Given:
        - List of fields of layouts with their values.

        When:
        - Creating a new dict representing a layout file.

        Then:
        - Ensure the expected dict is created.
        """
        assert self.layout_converter.create_layout_dict(**inputs) == expected

    def test_get_layouts_by_layout_container_type(self):
        """
        Given:
        - Layout container FileType.

        When:
        - Wanting to retrieve all layout-containers from the current pack.

        Then:
        - Ensure only layout-containers in the pack are returned.
        """
        layouts = self.layout_converter.get_layouts_by_layout_type(FileType.LAYOUTS_CONTAINER)
        assert all(layout.type() == FileType.LAYOUTS_CONTAINER for layout in layouts)
        assert [layout.layout_id() for layout in layouts] == ['ExtraHop Detection']

    def test_get_layouts_by_layout_type(self):
        """
        Given:
        - Layout FileType.

        When:
        - Wanting to retrieve all layout below 6.0.0 version from the current pack.

        Then:
        - Ensure only layouts below 6.0.0 version in the pack are returned.
        """
        layouts = self.layout_converter.get_layouts_by_layout_type(FileType.LAYOUT)
        assert len(layouts) == 5
        assert all(layout.type() == FileType.LAYOUT for layout in layouts)
        assert set(layout.get('kind') for layout in layouts) == {'close', 'details', 'edit', 'mobile', 'quickView'}

    def test_get_layout_dynamic_fields(self):
        """
        Given:
        - Schema path of the layouts-container.

        When:
        - Wanting to retrieve all dynamic fields in the schema.

        Then:
        - Ensure dynamic fields are returned.
        """
        dynamic_fields = set(self.layout_converter.get_layout_dynamic_fields(self.SCHEMA_PATH).keys())
        assert dynamic_fields == {'close', 'details', 'detailsV2', 'edit', 'indicatorsDetails', 'indicatorsQuickView',
                                  'mobile', 'quickView'}

    ENTITY_SEPARATORS_TO_UNDERSCORE_INPUTS = [('abcde', 'abcde'),
                                              ('axzjd-frl', 'axzjd_frl'),
                                              (f'''a{'a'.join(ENTITY_NAME_SEPARATORS)}a''',
                                               f'''a{'a'.join(['_'] * len(ENTITY_NAME_SEPARATORS))}a''')]

    @pytest.mark.parametrize('name, expected', ENTITY_SEPARATORS_TO_UNDERSCORE_INPUTS)
    def test_entity_separators_to_underscore(self, name: str, expected: str):
        """
        Given:
        - string, possibly containing one of the chars in 'ENTITY_NAME_SEPARATORS'.

        When:
        - Wanting to transform every char in 'ENTITY_NAME_SEPARATORS' to '_'.

        Then:
        - Ensure expected string is returned.
        """
        assert self.layout_converter.entity_separators_to_underscore(name) == expected

    def test_dump_new_layout(self):
        """
        Given:
        - 'new_layout_path': The path of the newly created layout.
        - 'new_layout_dict': The data of the new layout to be created.

        When:
        - Wanting to create a new file corresponding to 'new_layout_path' with the data of 'new_layout_dict'

        Then:
        - Ensure the file is created in the expected path and expected data.
        """
        self.layout_converter.dump_new_layout('test_layout', {'id': 'dummy_layout'})
        assert os.path.exists('test_layout')
        layout_data = util_load_json('test_layout')
        assert layout_data == {'id': 'dummy_layout'}
        os.remove('test_layout')

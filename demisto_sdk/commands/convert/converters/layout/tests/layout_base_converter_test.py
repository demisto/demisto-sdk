from demisto_sdk.commands.convert.converters.layout.layout_base_converter import LayoutBaseConverter
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.constants import FileType
import pytest
import os
from demisto_sdk.commands.common.legacy_git_tools import git_path
from typing import Dict
from demisto_sdk.commands.common.constants import FileType, ENTITY_NAME_SEPARATORS


# TODO add docs

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
        assert self.layout_converter.create_layout_dict(**inputs) == expected

    def test_get_layouts_by_layout_container_type(self):
        layouts = self.layout_converter.get_layouts_by_layout_type(FileType.LAYOUTS_CONTAINER)
        assert all(layout.type() == FileType.LAYOUTS_CONTAINER for layout in layouts)
        assert [layout.layout_id() for layout in layouts] == ['ExtraHop Detection']

    def test_get_layouts_by_layout_type(self):
        layouts = self.layout_converter.get_layouts_by_layout_type(FileType.LAYOUT)
        assert len(layouts) == 5
        assert all(layout.type() == FileType.LAYOUT for layout in layouts)
        assert set(layout.get('kind') for layout in layouts) == {'close', 'details', 'edit', 'mobile', 'quickView'}

    def test_get_layout_dynamic_fields(self):
        dynamic_fields = set(self.layout_converter.get_layout_dynamic_fields(self.SCHEMA_PATH).keys())
        assert dynamic_fields == {'close', 'details', 'detailsV2', 'edit', 'indicatorsDetails', 'indicatorsQuickView',
                                  'mobile', 'quickView'}

    def test_entity_separators_to_underscore(self):
        name = f'''a{'a'.join(ENTITY_NAME_SEPARATORS)}a'''
        num_of_separators = ['_'] * len(ENTITY_NAME_SEPARATORS)
        expected = f'''a{'a'.join(num_of_separators)}a'''
        assert self.layout_converter.entity_separators_to_underscore(name) == expected


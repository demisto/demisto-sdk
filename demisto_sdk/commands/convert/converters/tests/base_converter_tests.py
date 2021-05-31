import os
from typing import Union, Iterator, List

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import ClassifierObject
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import LayoutObject
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.base_converter import BaseConverter
from demisto_sdk.commands.common.constants import ENTITY_NAME_SEPARATORS
def util_load_json(path):
    with io.open(path, mode='r', encoding='utf-8') as f:
        return json.loads(f.read())
class TestBaseConverter:
    TEST_PACK_PATH = os.path.join(__file__,
                                  f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests/test_data/Packs'
                                  f'/ExtraHop')
    PACK_WITH_NEW_LAYOUTS_PATH = os.path.join(__file__,
                                              f'{git_path()}/demisto_sdk/commands/convert/converters/layout/tests'
                                              '/test_data/Packs'
                                              '/PackWithNewLayout')
    PACK = Pack(TEST_PACK_PATH)

    def test_get_layouts_by_layout_container_type(self):
        """
        Given:
        - Layout container FileType.

        When:
        - Wanting to retrieve all layout-containers from the current pack.

        Then:
        - Ensure only layout-containers in the pack are returned.
        """
        layouts = BaseConverter.get_entities_by_entity_type(self.PACK.layouts, FileType.LAYOUTS_CONTAINER)
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
        layouts = BaseConverter.get_entities_by_entity_type(self.PACK.layouts, FileType.LAYOUT)
        assert len(layouts) == 5
        assert all(layout.type() == FileType.LAYOUT for layout in layouts)
        assert {layout.get('kind') for layout in layouts} == {'close', 'details', 'edit', 'mobile', 'quickView'}

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

    def test_dump_new_entity(self):
        """
        Given:
        - 'new_entity_path': The path of the newly created entity.
        - 'new_entity_dict': The data of the new entity to be created.

        When:
        - Wanting to create a new file corresponding to 'new_entity_path' with the data of 'new_entity_dict'

        Then:
        - Ensure the file is created in the expected path and expected data.
        """
        self.layout_converter.('test_layout', {'id': 'dummy_layout'})
        assert os.path.exists('test_layout')
        layout_data = util_load_json('test_layout')
        assert layout_data == {'id': 'dummy_layout'}
        os.remove('test_layout')

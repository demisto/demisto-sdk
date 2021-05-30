import os
from typing import Union, Iterator, List

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import ClassifierObject
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import LayoutObject
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.base_converter import BaseConverter


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


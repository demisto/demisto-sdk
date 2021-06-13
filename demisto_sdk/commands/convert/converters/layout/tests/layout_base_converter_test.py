from typing import Dict

import pytest
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.layout.layout_base_converter import \
    LayoutBaseConverter


class TestLayoutBaseConverter:
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
        assert LayoutBaseConverter.create_layout_dict(**inputs) == expected

    def test_get_layout_dynamic_fields(self, tmpdir):
        """
        Given:
        - Schema path of the layouts-container.

        When:
        - Wanting to retrieve all dynamic fields in the schema.

        Then:
        - Ensure dynamic fields are returned.
        """
        dynamic_fields = set(LayoutBaseConverter(Pack(tmpdir)).get_layout_dynamic_fields().keys())
        assert dynamic_fields == {'close', 'details', 'detailsV2', 'edit', 'indicatorsDetails', 'indicatorsQuickView',
                                  'mobile', 'quickView'}

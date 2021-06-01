import shutil
from typing import Dict, List, Set

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import \
    LayoutObject
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.layout.layout_base_converter import \
    LayoutBaseConverter


class LayoutSixConverter(LayoutBaseConverter):

    def __init__(self, pack: Pack):
        super().__init__(pack)
        self.layout_indicator_fields = self.get_layout_indicator_fields()

    def convert_dir(self) -> int:
        """
        Converts old layouts in Layouts dir to the 6.0.0 layouts convention.
        Returns:
            (int): 0 if convert finished successfully, 1 otherwise.
        """
        old_layout_id_to_layouts_dict = self.group_layouts_needing_conversion_by_layout_id()
        for layout_id, old_corresponding_layouts in old_layout_id_to_layouts_dict.items():
            new_layout_dict = self.create_layout_dict(from_version='6.0.0', layout_id=layout_id)
            new_layout_dict['group'] = self.calculate_new_layout_group(old_corresponding_layouts)

            for old_layout in old_corresponding_layouts:
                layout_kind = old_layout.get('kind')
                if not layout_kind:
                    continue
                sections = old_layout.get_layout_sections()
                tabs = old_layout.get_layout_tabs()
                if sections:
                    new_layout_dict[layout_kind] = {'sections': sections}
                if tabs:
                    new_layout_dict[layout_kind] = {'tabs': tabs}

            self.update_incident_types_related_to_old_layouts(old_corresponding_layouts, layout_id)

            new_layout_path = self.calculate_new_layout_relative_path(layout_id)
            self.dump_new_entity(new_layout_path, new_layout_dict)

        return 0

    def get_layout_indicator_fields(self, schema_path: str = LayoutBaseConverter.DEFAULT_SCHEMA_PATH) -> Set[str]:
        """
        Calculates all the indicator fields in the layouts container schema.
        Args:
            schema_path (str): Path to the layouts container schema.
        Returns:
            (Set[str]): Set of all of the indicator field names in the layouts container schema.
        """
        return {schema_field for schema_field in self.get_layout_dynamic_fields(schema_path).keys()
                if 'indicator' in schema_field}

    def group_layouts_needing_conversion_by_layout_id(self) -> Dict[str, List[LayoutObject]]:
        """
        Builds list of old layouts needing conversion to 6.0.0 and above,
        returns a dict grouping layouts to layout ID as dict key, and list of layouts
        of the layouts with the corresponding layout ID.
        This logic is relevant as layout files below 6.0.0 have same layout ID if they are corresponding to same Layout
        structure.
        Args:

        Returns:
            (Dict[str, List[LayoutObject]]): Dict of (layoutID, [List of layouts with the corresponding layout ID).
        """
        layout_id_to_layouts_dict: Dict[str, List[LayoutObject]] = dict()
        for layout in self.get_entities_by_entity_type(self.pack.layouts, FileType.LAYOUT):
            layout_id = layout.layout_id()
            layout_id_to_layouts_dict[layout_id] = layout_id_to_layouts_dict.get(layout_id, []) + [layout]
        return layout_id_to_layouts_dict

    def calculate_new_layout_group(self, old_layouts: List[LayoutObject]) -> str:
        """
        Receives list of old layouts, calculates the group field for the new layout that will be created.
        Args:
            old_layouts (List[LayoutObject]): List of old layouts with same layout IDs.

        Returns:
            (str): The group type of the layouts.
        """
        is_group_indicator = any(layout.get('kind') in self.layout_indicator_fields for layout in old_layouts)
        return 'indicator' if is_group_indicator else 'incident'

    def calculate_new_layout_relative_path(self, layout_id: str) -> str:
        """
        Receives layout ID of the new layout to be created, calculates its path.
        Args:
            layout_id (str): The layout ID of the new layout to be created.

        Returns:
            (str): The path of the new layout to be created.
        """
        layout_base_name = self.entity_separators_to_underscore(layout_id)
        layout_file_name = f'{FileType.LAYOUTS_CONTAINER.value}-{layout_base_name}.json'
        new_layout_path = f'{str(self.pack.path)}/Layouts/{layout_file_name}'

        return new_layout_path

    def update_incident_types_related_to_old_layouts(self, old_layouts: List[LayoutObject], layout_id: str) -> None:
        """
        Receives list of old layouts, updates related incident types with the layout field.
        Args:
            old_layouts (List[LayoutObject]): List of the old layouts.
            layout_id (str): Layout ID of the given old layouts.

        Returns:
            (None): Updates the related incident types.
        """
        old_layouts_type_ids = {layout.get('typeId') for layout in old_layouts}
        bounded_incident_types = [incident_type for incident_type in self.pack.incident_types
                                  if incident_type.get('id') in old_layouts_type_ids]
        for bounded_incident_type in bounded_incident_types:
            bounded_incident_type['layout'] = layout_id
            try:
                bounded_incident_type.dump()
            except shutil.SameFileError:
                pass

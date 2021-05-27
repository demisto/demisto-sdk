from typing import List, Dict

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.convert.converters.layout.layout_base_converter import LayoutBaseConverter


class LayoutBelowSixConverter(LayoutBaseConverter):

    def __init__(self, pack: Pack):
        super().__init__(pack)

    def convert_dir(self) -> int:
        """
        Converts new layouts in Layouts dir to the below 6.0.0 layouts convention.
        Returns:
            (int): 0 if convert finished successfully, 1 otherwise.
        """
        layouts_to_be_converted = self.get_layouts_by_layout_type(FileType.LAYOUTS_CONTAINER)
        layout_id_to_incident_type_id_dict = self.create_layout_id_to_incident_types_id_dict()
        layout_dynamic_fields = self.get_layout_dynamic_fields()
        for layout_to_convert in layouts_to_be_converted:

            if (layout_id := layout_to_convert.layout_id()) not in layout_id_to_incident_type_id_dict:
                # TODO Log statement
                continue
            if not (incident_type_ids := layout_id_to_incident_type_id_dict.get(layout_id)):
                # TODO Log statement
                continue
            for incident_type_id in incident_type_ids:
                for dynamic_field_key, dynamic_field_value in layout_dynamic_fields.items():
                    new_layout_dict = self.create_layout_dict(from_version='4.1.0', to_version='5.9.9',
                                                              type_id=incident_type_id, kind=dynamic_field_key)
                    new_layout_dict['layouts'] = dict(id=layout_id, name=layout_id, version=-1, kind=dynamic_field_key,
                                                      typeId=incident_type_id)
                    if isinstance(dynamic_field_value, dict):
                        new_layout_dict.update(dynamic_field_value)
                    new_layout_path = self.calculate_new_layout_relative_path(layout_id, dynamic_field_key,
                                                                              incident_type_id)

                    self.dump_new_layout(new_layout_path, new_layout_dict)
        return 0

    def calculate_new_layout_relative_path(self, layout_id: str, dynamic_field_key: str, incident_type_id: str) -> str:
        """
        Receives layout ID of the new layout to be created, calculates its path.
        Args:
            layout_id (str): The layout ID of the new layout to be created.
            dynamic_field_key (str): The dynamic key field name of whom the new layout will be created from.
            incident_type_id (str): Incident type whom ID is bounded to the layout.

        Returns:
            (str): The path of the new layout to be created, following the expected format for layouts below 6.0.0.
        """
        layout_name = self.entity_separators_to_underscore(layout_id)
        fixed_incident_type_id = self.entity_separators_to_underscore(incident_type_id)
        layout_file_name = f'{FileType.LAYOUT.value}-{dynamic_field_key}-{layout_name}-{fixed_incident_type_id}.json'
        new_layout_path = f'{str(self.pack.path)}/Layouts/{layout_file_name}'

        return new_layout_path

    #         TODO: check here for connected incident types (maybe indicator types too)

    def create_layout_id_to_incident_types_id_dict(self) -> Dict[str, List[str]]:
        """
        Iterates through incident types in the pack, builds a dict of {layoutID: [List of incident type IDs]}.
        where the list of the incident type IDs are the list of all the incident types whom layout field has
        corresponding ID to the layoutID field.
        Returns:
            (Dict[str, List[str]): Dict of {layoutID: [List of incident type IDs]}.
        """
        layout_id_to_incident_types_id_dict: Dict[str, List[str]] = dict()
        for incident_type in self.pack.incident_types:
            if not (incident_layout_id := incident_type.get('layout')):
                # TODO debug statement
                continue
            if not (incident_type_id := incident_type.get('id')):
                # TODO debug statement
                continue
            layout_id_to_incident_types_id_dict[incident_layout_id] = layout_id_to_incident_types_id_dict.get(
                incident_layout_id, []) + [incident_type_id]
        return layout_id_to_incident_types_id_dict

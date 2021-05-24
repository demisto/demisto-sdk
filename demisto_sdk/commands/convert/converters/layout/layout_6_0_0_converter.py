from demisto_sdk.commands.convert.converters.abstract_converter import AbstractConverter
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from typing import Set


class LayoutSixConverter(AbstractConverter):

    def __init__(self, pack: Pack):
        super().__init__()
        self.pack = pack
        schema_data: dict = get_yaml(
            '/Users/tneeman/dev/demisto/demisto-sdk/demisto_sdk/commands/common/schemas/layoutscontainer.yml')
        schema_mapping = schema_data.get('mapping', dict())
        self.layout_indicator_fields = {schema_field for schema_field, schema_value in schema_mapping.items()
                                        if 'mapping' in schema_value and 'indicator' in schema_field}

    def convert_dir(self):
        layouts = [layout for layout in self.pack.layouts]
        layouts_6_0_0_and_above_ids: Set[str] = {layout.get_layout_id() for layout in layouts
                                                 if find_type(str(layout.path)) == FileType.LAYOUTS_CONTAINER
                                                 and layout.get_layout_id() is not None}
        # We will convert layouts below 6_0_0 versions that don't have a corresponding layout 6_0_0 and above version.
        layouts_needed_conversions = [layout for layout in layouts if find_type(str(layout.path)) == FileType.LAYOUT
                                      if layout.get_layout_id() not in layouts_6_0_0_and_above_ids]


import json
import os
import shutil
from tempfile import mkdtemp
from typing import Tuple

from demisto_sdk.commands.common.constants import (ENTITY_NAME_SEPARATORS,
                                                   INCIDENT_TYPES_DIR,
                                                   LAYOUTS_DIR, FileType)
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type,
                                               get_child_files, get_json,
                                               get_yaml, print_color)
from tabulate import tabulate


class LayoutConverter:
    def update_new_layout(self, input_pack_path, layout_object, layout_id, old_layouts):
        new_layout: dict = self.get_new_layout(layout_object, layout_id)
        new_layout_path: str = new_layout.get('file_object').get('path')
        data: dict = new_layout.get('data')
        is_group_indicator: bool = False

        for old_layout in old_layouts:
            old_data = old_layout.get('data')
            old_layout_kind = old_data.get('kind')

            if old_layout_kind:
                # Update group field
                is_group_indicator = is_group_indicator or old_layout_kind in self.layout_indicator_fields
                if is_group_indicator and not data['group']:
                    data['group'] = 'indicator'

                # Update dynamic fields
                sections = old_data.get('layout', {}).get('sections', [])
                if sections:
                    data[old_layout_kind] = {'sections': sections}

                tabs = old_data.get('layout', {}).get('tabs', [])
                if tabs:
                    data[old_layout_kind] = {'tabs': tabs}

        # Update group field
        if not is_group_indicator:
            data['group'] = 'incident'

        with open(new_layout_path, 'w') as jf:
            json.dump(obj=data, fp=jf, indent=4)

        self.update_bounded_it(input_pack_path, layout_id, old_layouts)

    @staticmethod
    def create_new_layout(layout_id, layouts_tempdir_path):
        data = dict()
        data["fromVersion"] = "6.0.0"
        data["group"] = ""  # to be defined in update_new_layout
        data["name"] = layout_id
        data["id"] = layout_id
        data["version"] = -1

        new_layout_basename = layout_id
        for separator in ENTITY_NAME_SEPARATORS:
            new_layout_basename = new_layout_basename.replace(separator, '_')
        new_layout_basename = f'{FileType.LAYOUTS_CONTAINER.value}-{new_layout_basename}.json'
        new_layout_temp_path = os.path.join(layouts_tempdir_path, new_layout_basename)
        with open(new_layout_temp_path, 'w') as jf:
            json.dump(obj=data, fp=jf)

        return new_layout_temp_path

    def support_new_format(self, input_pack_path, pack_layouts_tempdir_path, pack_layouts_object):
        for layout_id, layout_object in pack_layouts_object.items():
            new_layout_created: bool = False
            old_layouts = self.get_old_layouts(layout_object)
            if not layout_object['>=6.0_exist']:
                new_layout_temp_path = self.create_new_layout(layout_id, pack_layouts_tempdir_path)
                pack_layouts_object[layout_id]['files'].append({'path': new_layout_temp_path, 'version': '>=6.0'})
                pack_layouts_object[layout_id]['>=6.0_exist'] = True
                new_layout_created = True
                self.update_new_layout(input_pack_path, layout_object, layout_id, old_layouts)
                total_supporting_layouts = 1 if new_layout_created else 0
                self.log_converted_layout(layout_id, '<6.0', '>=6.0', total_supporting_layouts, 1, 0, 0, [],
                                          input_pack_path)
            else:
                self.update_new_layout(input_pack_path, layout_object, layout_id, old_layouts)
            self.update_old_layouts(old_layouts)

    """
    LayoutConverter is a class that's designed to convert a local layout in content repository from old format
    to 6.0 format.

    Attributes:
        input_packs (list): The list of input packs to make conversions in
        pack_tempdirs (list): A dict of all corresponding pack temporary directories
    """

    def __init__(self, input: str, six_to_five: bool, five_to_six: bool):
        self.input_packs = list(input)
        self.new_to_old: bool = six_to_five
        self.old_to_new: bool = five_to_six
        self.pack_tempdirs: dict = {pack: mkdtemp() for pack in self.input_packs}
        self.schema_path: str = os.path.normpath(os.path.join(__file__, '..', '..', 'common/schemas/',
                                                              f'{FileType.LAYOUTS_CONTAINER.value}.yml'))
        self.schema_data: dict = get_yaml(self.schema_path)
        self.layout_dynamic_fields: list = [f for f, _ in self.schema_data.get('mapping').items() if
                                            self.schema_data.get('mapping').get(f).get('mapping')]
        self.layout_indicator_fields: list = [f for f in self.layout_dynamic_fields if 'indicator' in f]
        self.layouts_not_converted: dict = {pack: list() for pack in self.input_packs}
        self.printed_packs: dict = {pack: {'old': False, 'new': False} for pack in self.input_packs}

    def convert(self) -> int:
        """
        Manages all conversions
        :return The exit code of each flow
        """
        if not self.verify_input_packs_is_pack():
            return 1
        if not self.verify_flags():
            return 1
        first: bool = True
        last: bool = True
        for input_pack in self.input_packs:
            self.log_pack_name(input_pack, newline_start=first)
            first = False
            pack_layouts_path: str = os.path.join(input_pack, LAYOUTS_DIR)
            pack_layouts_tempdir_path: str = self.copy_layouts_to_tempdir(input_pack)
            pack_layouts_object: dict = self.build_pack_layouts_object(input_pack, pack_layouts_tempdir_path)
            if self.new_to_old:
                self.support_old_format(input_pack, pack_layouts_tempdir_path, pack_layouts_object)
            if self.old_to_new:
                self.support_new_format(input_pack, pack_layouts_tempdir_path, pack_layouts_object)
            self.replace_layouts_dir(pack_layouts_tempdir_path, pack_layouts_path)
            if input_pack == self.input_packs[-1]:
                last = False
            self.log_layouts_not_converted(input_pack)
            self.log_pack_name(input_pack, newline_end=last)
        self.remove_traces()
        return 0

    def copy_layouts_to_tempdir(self, input_pack_path: str) -> str:
        """
        @TODO:
        :param input_pack_path: @TODO:
        :return: @TODO:
        """
        try:
            pack_tempdir_path: str = self.pack_tempdirs.get(input_pack_path)
            pack_layouts_tempdir_path: str = os.path.join(pack_tempdir_path, LAYOUTS_DIR)
            shutil.copytree(src=os.path.join(input_pack_path, LAYOUTS_DIR), dst=pack_layouts_tempdir_path)
            return pack_layouts_tempdir_path
        except shutil.Error as e:
            print(f'Shutil Error: {str(e)}')

    def build_pack_layouts_object(self, input_pack: str, pack_layouts_tempdir_path: str) -> dict:
        pack_layouts_object: dict = dict()
        files: list = get_child_files(pack_layouts_tempdir_path)
        is_new_exist_in_pack: bool = False
        is_old_exist_in_pack: bool = False

        for file_path in files:
            file_data: dict = get_json(file_path)
            if find_type(path=file_path, _dict=file_data, file_type='json') in [FileType.LAYOUT,
                                                                                FileType.LAYOUTS_CONTAINER]:
                layout_version: str = self.get_layout_version(file_data)
                layout_id: str = self.get_layout_id(file_data, layout_version)
                file_object: dict = {'path': file_path, 'version': layout_version}
                is_old_version: bool = layout_version == '<6.0'
                is_old_exist_in_pack = is_old_exist_in_pack or is_old_version
                is_new_version: bool = layout_version == '>=6.0'
                is_new_exist_in_pack = is_new_exist_in_pack or is_new_version

                # Update existing layout in the pack layouts object
                if layout_id in pack_layouts_object:
                    pack_layouts_object[layout_id]['files'].append(file_object)
                    pack_layouts_object[layout_id]['>=6.0_exist'] = pack_layouts_object[layout_id]['>=6.0_exist'] \
                                                                    or is_new_version
                    pack_layouts_object[layout_id]['<6.0_exist'] = pack_layouts_object[layout_id]['<6.0_exist'] \
                                                                   or is_old_version
                # Insert new layout to the pack layouts object
                else:
                    pack_layouts_object[layout_id] = {
                        'files': [file_object],
                        '>=6.0_exist': is_new_version,
                        '<6.0_exist': is_old_version
                    }

        if pack_layouts_object and not is_old_exist_in_pack and self.old_to_new:
            print_color(f'* No old layouts found in {os.path.basename(input_pack)} Pack.\n',
                        LOG_COLORS.NATIVE)

        if pack_layouts_object and not is_new_exist_in_pack and self.new_to_old:
            print_color(f'* No new layouts found in {os.path.basename(input_pack)} Pack.\n',
                        LOG_COLORS.NATIVE)

        if not pack_layouts_object:
            print_color(f'* No layouts were found in {os.path.basename(input_pack)} Pack.\n',
                        LOG_COLORS.NATIVE)

        return pack_layouts_object

    def support_old_format(self, input_pack_path: str, pack_layouts_tempdir_path: str, pack_layouts_object: dict):
        for layout_id, layout_object in pack_layouts_object.items():
            if layout_object['>=6.0_exist']:
                new_layout: dict = self.get_new_layout(layout_object, layout_id)
                new_layout_data: dict = new_layout.get('data')
                dynamic_fields, static_fields = self.get_layout_fields(new_layout_data)
                num_new_layouts: int = 0

                connected_its = self.get_connected_its(layout_id, input_pack_path)
                if not connected_its:
                    self.layouts_not_converted[input_pack_path].append([
                        os.path.basename(input_pack_path),
                        layout_id,
                        '>=6.0',
                        'Cannot convert new layout to old layout if there is no incident type bounded to it'
                    ])

                else:
                    # For each IncidentType connected to the new layout we need to create an old layout
                    # in Demisto versions <6.0 each layout is connected to an incident type
                    for type_id in connected_its:
                        for key, value in dynamic_fields.items():
                            if not self.is_kind_layout_exist(key, layout_object, type_id):
                                old_layout_temp_path: str = self.create_old_layout(key, value, type_id,
                                                                                   pack_layouts_tempdir_path, layout_id)
                                pack_layouts_object[layout_id]['files'].append({
                                    'path': old_layout_temp_path,
                                    'version': '<6.0'
                                })
                                pack_layouts_object[layout_id]['<6.0_exist'] = True
                                num_new_layouts += 1
                            else:
                                # @TODO: might not be needed
                                # self.update_old_layout({key: value}, static_fields, layout_id)
                                pass

                    num_bounded_its: int = len(connected_its)
                    num_dynamic_fields: int = len(dynamic_fields)
                    total_layouts: int = num_bounded_its * num_dynamic_fields
                    self.log_converted_layout(layout_id, '>=6.0', '<6.0', num_new_layouts, total_layouts,
                                              num_dynamic_fields, num_bounded_its, connected_its, input_pack_path)

            else:
                pass

    def get_layout_fields(self, new_layout_data: dict) -> Tuple[dict, dict]:
        """
        @TODO:
        :param new_layout_data: @TODO:
        :return: @TODO:
        """
        dynamic_fields: dict = dict()
        static_fields: dict = dict()
        for key, value in new_layout_data.items():
            # Check if it's a kind section
            if key in self.layout_dynamic_fields:
                dynamic_fields[key] = value
            else:
                static_fields[key] = value
        return dynamic_fields, static_fields

    @staticmethod
    def get_connected_its(layout_id: str, pack_path: str) -> list:
        """
        @TODO:
        :param layout_id: @TODO:
        :param pack_path: @TODO:
        :return: @TODO:
        """
        its_ids_list: list = list()
        for file in get_child_files(os.path.join(pack_path, INCIDENT_TYPES_DIR)):
            if find_type(path=file) == FileType.INCIDENT_TYPE:
                it_data = get_json(file)
                if 'layout' in it_data and it_data['layout'] == layout_id:
                    its_ids_list.append(it_data.get('id'))
        return its_ids_list

    def is_kind_layout_exist(self, kind_field_key: str, layout_object: dict, type_id: str) -> bool:
        """
        @TODO:
        :param layout_object: @TODO:
        :param kind_field_key: @TODO:
        :param type_id: @TODO:
        :return: @TODO:
        """
        old_layouts_data: list = [ol.get('data') for ol in self.get_old_layouts(layout_object)]
        return any(old_layout_data.get('kind') == kind_field_key and old_layout_data.get('typeId') == type_id
                   for old_layout_data in old_layouts_data)

    def create_old_layout(self, key: str, value, raw_type_id: str, layouts_temp_path: str, layout_id: str) -> str:
        """
        @TODO:
        :param key: @TODO:
        :param value: @TODO:
        :param raw_type_id: @TODO:
        :param layouts_temp_path: @TODO:
        :param layout_id: @TODO:
        :return: @TODO:
        """
        old_layout_basename: str = layout_id
        type_id: str = raw_type_id
        for separator in ENTITY_NAME_SEPARATORS:
            old_layout_basename = old_layout_basename.replace(separator, '_')
            type_id = type_id.replace(separator, '_')

        data: dict = dict()
        data['kind'] = key
        data['layout'] = self.build_section_layout(key, value, layout_id, raw_type_id)
        data['fromVersion'] = '4.1.0'
        data['toVersion'] = '5.9.9'
        data['typeId'] = raw_type_id
        data['version'] = -1

        old_layout_basename = f'{FileType.LAYOUT.value}-{key}-{old_layout_basename}-{type_id}.json'
        old_layout_temp_path: str = os.path.join(layouts_temp_path, old_layout_basename)

        with open(old_layout_temp_path, 'w') as jf:
            json.dump(obj=data, fp=jf, indent=4)

        return old_layout_temp_path

    @staticmethod
    def build_section_layout(key, value, layout_id, type_id):
        """
        @TODO:
        :param key: @TODO:
        :param value: @TODO:
        :param layout_id: @TODO:
        :param type_id: @TODO:
        :return: @TODO:
        """
        section_layout: dict = dict()
        section_layout['id'] = layout_id
        section_layout['name'] = layout_id
        section_layout['version'] = -1
        section_layout['kind'] = key
        section_layout['typeId'] = type_id
        if value and isinstance(value, dict):
            section_layout.update(value)
        return section_layout

    @staticmethod
    def update_old_layout(kind_field, non_kind_fields, layout_id):
        """
        @TODO:
        :param kind_field: @TODO:
        :param non_kind_fields: @TODO:
        :param layout_id: @TODO:
        :return: @TODO:
        """
        pass

    @staticmethod
    def replace_layouts_dir(pack_layouts_tempdir_path, pack_layouts_path):
        # Switch between the layouts temp dir to original one
        try:
            shutil.rmtree(pack_layouts_path)
            shutil.move(src=pack_layouts_tempdir_path, dst=pack_layouts_path)
        except shutil.Error as e:
            print(f'Shutil Error: {str(e)}')

    @staticmethod
    def get_layout_id(layout_data: dict, layout_version: str):
        if layout_version == '<6.0':
            return layout_data.get('layout', {}).get('id')
        return layout_data.get('id')

    @staticmethod
    def get_layout_version(layout_data: dict):
        if 'layout' in layout_data:
            return '<6.0'
        return '>=6.0'

    @staticmethod
    def update_old_layouts(old_layouts):
        for layout in old_layouts:
            data = layout.get('data')
            path = layout.get('file_object', {}).get('path')
            if 'toVersion' not in data:
                data["toVersion"] = "5.9.9"
            if 'fromVersion' not in data:
                data["fromVersion"] = "4.1.0"
            # TODO: Check if more fields are needed
            with open(path, 'w') as jf:
                json.dump(obj=data, fp=jf, indent=4)

    @staticmethod
    def update_bounded_it(pack_path: str, layout_id: str, old_layouts: list):
        type_ids = list({ol.get('data').get('typeId') for ol in old_layouts})
        files = get_child_files(os.path.join(pack_path, INCIDENT_TYPES_DIR))
        its: list = list()
        for file in files:
            file_data = get_json(file)
            if find_type(path=file, _dict=file_data, file_type='json') == FileType.INCIDENT_TYPE:
                its.append({'data': file_data, 'path': file})
        its = [x for x in its if x['data'].get('id') in type_ids]
        for it in its:
            it['data']['layout'] = layout_id
            with open(it['path'], 'w') as jf:
                json.dump(obj=it['data'], fp=jf, indent=4)

    @staticmethod
    def get_old_layouts(layout_object) -> list:
        return [{'file_object': file_object, 'data': get_json(file_object.get('path'))}
                for file_object in layout_object.get('files', []) if file_object.get('version') == '<6.0']

    @staticmethod
    def get_new_layout(layout_object, layout_id) -> dict:
        new_layout: dict = dict()
        num_new_layouts = 0

        for file_object in layout_object.get('files', []):
            if file_object.get('version') == '>=6.0':
                new_layout = file_object
                num_new_layouts += 1

        if num_new_layouts != 1:
            # @TODO: Think if need to raise here
            raise Exception(f'Error: Found more than 1 new 6.0 format layout with id: {layout_id}')

        return {'file_object': new_layout, 'data': get_json(new_layout.get('path'))}

    def remove_traces(self):
        """
        Removes (recursively) all temporary files & directories used across the module
        """
        try:
            for _, pack_tempdir in self.pack_tempdirs.items():
                shutil.rmtree(pack_tempdir, ignore_errors=True)
        except shutil.Error as e:
            print_color(e, LOG_COLORS.RED)
            raise

    def verify_input_packs_is_pack(self) -> bool:
        """
        Verifies the input pack paths entered by the user are an actual pack path in content repository.
        :return: The verification result
        """
        input_packs_path_list: list = self.input_packs
        ans: bool = True
        err_msg: str = str()
        for input_pack_path in input_packs_path_list:
            if not (os.path.isdir(input_pack_path) and
                    os.path.basename(os.path.dirname(os.path.abspath(input_pack_path))) == 'Packs' and
                    os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(input_pack_path)))) == 'content'):
                err_msg += f'{input_pack_path},'
                ans = ans and False
        if not ans:
            print_color(f"{err_msg.strip(',')} don't have the format of a valid pack path. The designated output "
                        f"pack's path is of format ~/.../content/Packs/$PACK_NAME", LOG_COLORS.RED)
        return ans

    def verify_flags(self) -> bool:
        """
        @TODO:
        :return: @TODO:
        """

        if not any((self.new_to_old, self.old_to_new)):
            self.old_to_new = True
            self.new_to_old = True
        return True

    def log_layouts_not_converted(self, pack: str):
        """
        @TODO:
        :return: @TODO:
        """
        if self.layouts_not_converted[pack]:
            print_color("Failed to convert the following layouts:\n", LOG_COLORS.RED)
            print_color(tabulate(self.layouts_not_converted[pack], headers=['PACK', 'LAYOUT', 'VERSION', 'REASON']),
                        LOG_COLORS.RED)
            print()

    def log_converted_layout(self, layout_id: str, from_version: str, to_version: str, num_new_layouts: int,
                             total_layouts: int, num_dynamic_fields: int, num_bounded_its: int, connected_its: list,
                             input_pack: str):
        """
        @TODO:
        :param layout_id: @TODO:
        :param from_version: @TODO:
        :param to_version: @TODO:
        :param num_new_layouts: @TODO:
        :param total_layouts: @TODO:
        :param num_dynamic_fields: @TODO:
        :param num_bounded_its: @TODO:
        :param connected_its: @TODO:
        :param input_pack: @TODO:
        :return: @TODO:
        """
        added_version: str = 'new' if to_version == '>=6.0' else 'old'
        if num_new_layouts > 0:
            self.printed_packs[input_pack][added_version] = True
            print('-', end='')
            print_color(f" Converted '{layout_id}' layout from version '{from_version}' to version '{to_version}'.",
                        LOG_COLORS.GREEN, end='')
            print_color(f"\n  Total: {num_new_layouts} {added_version} version"
                        f" {'layouts were' if num_new_layouts > 1 else 'layout was'} added.\n"
                        f"  The '{layout_id}' layout is {added_version} version supported by "
                        f'{total_layouts} {added_version} format {"layouts" if total_layouts > 1 else "layout"}.',
                        LOG_COLORS.NATIVE)
            if num_dynamic_fields and total_layouts > num_dynamic_fields:
                print_color(f"  There are {num_bounded_its} times the amount of {added_version} layouts, because there"
                            f" are {num_bounded_its} bounded incident types to '{layout_id}' layout {connected_its}"
                            f".", LOG_COLORS.NATIVE)
            print()

        else:
            pass
            # print_color(f"- The '{layout_id}' layout is already {added_version} version supported by "
            #             f'{total_layouts} {added_version} {"layouts" if total_layouts > 1 else "layout"}.'
            #             f' No {added_version} layouts were added.',
            #             LOG_COLORS.NATIVE)

    @staticmethod
    def log_pack_name(input_pack_path: str, newline_end: bool = False, newline_start: bool = False):
        """
        @TODO:
        :param input_pack_path: @TODO:
        :param newline_end: @TODO:
        :param newline_start: @TODO:
        :return: @TODO:
        """
        separator: str = '============================================================'
        if newline_start:
            print()
        print_color(f'{separator} {os.path.basename(input_pack_path)} Pack {separator}\n', LOG_COLORS.NATIVE)
        if newline_end:
            print()

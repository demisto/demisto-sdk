import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from tempfile import *
import tarfile
import os
import ast
import io
import shutil

from demisto_sdk.commands.common.tools import get_files_in_dir, get_child_directories, get_yml_paths_in_dir, \
    get_id_by_content_entity, get_yaml, get_child_files, get_json, remove_trailing_backslash, \
    retrieve_file_ending, arg_to_list, get_dict_from_file, find_type, get_name_by_content_entity
from demisto_sdk.commands.split_yml.extractor import Extractor
from demisto_sdk.commands.common.constants import CONTENT_ENTITIES_DIRS, CONTENT_FILE_ENDINGS, \
    INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR, BETA_INTEGRATIONS_DIR, ENTITY_TYPE_TO_DIR


class Downloader:
    """TODO: add docs, add logging
    """

    def __init__(self, output: str, input: str, force: bool = False, insecure: bool = False, verbose: bool = False):
        self.output_pack_path = output
        self.input_files = arg_to_list(input)
        self.force = force
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)
        self.custom_content_temp_dir = mkdtemp()
        self.custom_content = list()
        self.pack_content = {entity: list() for entity in CONTENT_ENTITIES_DIRS}
        self.SPECIAL_ENTITIES = {TEST_PLAYBOOKS_DIR: PLAYBOOKS_DIR, BETA_INTEGRATIONS_DIR: INTEGRATIONS_DIR}

    def download(self) -> int:
        """TODO: might need to implement light mode, just on needed files, add logging
        Syncs downloaded data from demisto to content repository
        """
        self.verify_path_is_pack()
        self.build_pack_content()
        self.fetch_custom_content()
        self.build_custom_content()
        self.update_pack_hierarchy()
        self.merge_into_pack()
        self.remove_traces()
        self.log_to_user()
        return 0

    def verify_path_is_pack(self) -> None:
        """TODO: add unit test, implement, add logging
        Verifies the input path entered by the user is an actual pack path in content repository
        """
        pass

    def build_pack_content(self) -> None:
        """TODO: add docs, add unit test, add logging
        """
        for content_entity_path in get_child_directories(self.output_pack_path):
            raw_content_entity: str = os.path.basename(remove_trailing_backslash(content_entity_path))
            content_entity: str = self.SPECIAL_ENTITIES.get(raw_content_entity, raw_content_entity)
            child_dirs: list = get_child_directories(content_entity_path)
            entity_instances_paths: list = child_dirs if child_dirs else get_child_files(content_entity_path)
            for entity_instance_path in entity_instances_paths:
                content_object: dict = self.build_pack_content_object(content_entity, entity_instance_path)
                self.pack_content[content_entity].append(content_object)

    def build_pack_content_object(self, content_entity: str, entity_instance_path: str) -> dict:
        """TODO: add docs, add unit test, add logging
        """
        file_paths: list = get_files_in_dir(entity_instance_path, CONTENT_FILE_ENDINGS, recursive=False)
        main_id, main_data, main_file_path, main_name = self.get_main_file_details(content_entity, entity_instance_path)
        content_object: dict = {main_name: list()}

        for file_path in file_paths:
            content_object[main_name].append({
                'name': main_name,
                'id': main_id,
                'path': file_path,
                'data': main_data if main_file_path == file_path else {},
                'file_ending': retrieve_file_ending(file_path)
            })

        return content_object

    @staticmethod
    def get_main_file_details(content_entity: str, entity_instance_path: str) -> tuple:
        """TODO: add docs, add unit test, add logging
        """
        main_file_data: dict = dict()
        main_file_path: str = str()

        # Entities which contain yml files
        if content_entity in (INTEGRATIONS_DIR, BETA_INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR):
            if os.path.isdir(entity_instance_path):
                _, main_file_path = get_yml_paths_in_dir(entity_instance_path)
            elif os.path.isfile(entity_instance_path):
                main_file_path = entity_instance_path

            main_file_data = get_yaml(main_file_path)

        # Entities which are json files (md files are ignored)
        else:
            if os.path.isfile(entity_instance_path) and entity_instance_path.endswith('json'):
                main_file_path = entity_instance_path
                main_file_data = get_json(entity_instance_path)

        main_id = get_id_by_content_entity(main_file_data, content_entity)
        main_name = get_name_by_content_entity(main_file_data, content_entity)

        return main_id, main_file_data, main_file_path, main_name

    def fetch_custom_content(self) -> None:
        """TODO: add docs, add unit test, add logging
        """
        try:
            api_response: tuple = demisto_client.generic_request_func(self.client, '/content/bundle', 'GET')
            body: bytes = ast.literal_eval(api_response[0])
            io_bytes = io.BytesIO(body)
            tar = tarfile.open(fileobj=io_bytes, mode='r')

            for member in tar.getmembers():
                file_name: str = self.update_file_prefix(remove_trailing_backslash(member.name))
                with open(os.path.join(self.custom_content_temp_dir, file_name), 'w') as file:
                    file.write(tar.extractfile(member).read().decode('utf-8'))

        except ApiException as e:
            print(f'Exception raised when fetching custom content: {e}')

    @staticmethod
    def update_file_prefix(file_name: str) -> str:
        """TODO: add docs, add unit test, add logging
        """
        if file_name.startswith('automation-'):
            return file_name.replace('automation-', 'script-')
        return file_name

    def build_custom_content(self) -> None:
        """TODO: add docs, add unit test
        """
        files_paths: list = get_child_files(self.custom_content_temp_dir)
        for file_path in files_paths:
            custom_content_object: dict = self.build_custom_content_object(file_path)
            for input_file_name in self.input_files:
                name = custom_content_object['name']
                if name == input_file_name:
                    entity: str = custom_content_object['entity']
                    exist_in_pack: bool = False
                    for entity_instance_object in self.pack_content[entity]:
                        if entity_instance_object.get(name):
                            exist_in_pack = True
                    custom_content_object['exist_in_pack'] = exist_in_pack
                    self.custom_content.append(custom_content_object)

    @staticmethod
    def build_custom_content_object(file_path: str) -> dict:
        """TODO: add docs, add unit test
        """
        file_data, file_ending = get_dict_from_file(file_path)
        file_type: str = find_type(_dict=file_data, file_type=file_ending)
        file_entity: str = ENTITY_TYPE_TO_DIR.get(file_type)
        file_id: str = get_id_by_content_entity(file_data, file_entity)
        file_name: str = get_name_by_content_entity(file_data, file_entity)
        return {
            'id': file_id,
            'name': file_name,
            'path': file_path,
            'entity': file_entity,
            'type': file_type,
            'file_ending': file_ending,
            'data': file_data
        }

    @staticmethod
    def get_artificial_file_name(file_path: str) -> str:
        """TODO: add unit test
        Retrieves the artificial file name of the temporary file
        :param file_path: The original file path
        :return: The artificial file name
        """
        path: str = os.path.basename(file_path)
        split: list = path.split('###')
        return split[0] + split[2]

    def update_pack_hierarchy(self) -> None:
        """TODO: add unit test
        Add all entity dirs missing
        Add all entity instance dirs missing
        :return: None
        """
        for custom_content_object in self.custom_content:
            file_entity: str = custom_content_object['entity']
            file_name: str = custom_content_object['name']
            entity_path: str = os.path.join(self.output_pack_path, file_entity)
            if not os.path.isdir(entity_path):
                os.mkdir(entity_path)
            entity_instance_path: str = os.path.join(entity_path, self.create_dir_name(file_name))
            if not os.path.isdir(entity_instance_path) and file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                os.mkdir(entity_instance_path)

    @staticmethod
    def create_dir_name(file_name: str) -> str:
        """TODO: add unit test
        :param file_name: The file name
        :return: The dir name corresponding to the file name
        """
        dir_name: str = file_name
        name_separators: list = [' ', '_', '-']
        for separator in name_separators:
            dir_name = dir_name.replace(separator, '')
        return dir_name

    def merge_into_pack(self) -> None:
        """TODO: add docs, add unit test, add logging
        """
        for custom_content_object in self.custom_content:
            file_entity: str = custom_content_object['entity']
            file_path: str = custom_content_object['path']
            if custom_content_object['exist_in_pack']:
                if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                    pass
                else:
                    pass
            else:
                output_path: str = os.path.join(self.output_pack_path, file_entity)
                if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                    file_name: str = custom_content_object['name']
                    dir_name: str = self.create_dir_name(file_name)
                    output_path: str = os.path.join(output_path, dir_name)
                    file_type: str = custom_content_object['type']
                    if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                        extractor = Extractor(input=file_path, output=output_path, file_type=file_type,
                                              base_name=dir_name, no_auto_create_dir=True, no_logging=True)
                        extractor.extract_to_package_format()
                else:
                    file_name: str = os.path.basename(file_path)
                    output_path: str = os.path.join(output_path, file_name)
                    shutil.move(src=file_path, dst=output_path)

    def remove_traces(self):
        """TODO: add unit test
        Removes (recursively) all temporary files & directories used across the module
        """
        shutil.rmtree(self.custom_content_temp_dir, ignore_errors=True)

    def log_to_user(self) -> None:
        """TODO: add docs
        :return: None
        """
        pass

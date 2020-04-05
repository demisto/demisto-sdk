import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from tempfile import *
import tarfile
import os
import ast
import io
import shutil

from demisto_sdk.commands.common.tools import get_files_in_dir, get_child_directories, get_yml_paths_in_dir, \
    get_id_by_content_entity, get_yaml, get_child_files, get_json, get_file_data, remove_trailing_backslash, \
    retrieve_file_ending, retrieve_module_from_file
from demisto_sdk.commands.split_yml.extractor import Extractor
from demisto_sdk.commands.common.constants import CONTENT_ENTITIES_DIRS, CONTENT_FILE_ENDINGS, CONTENT_PREFIXES, \
    CUSTOM_CONTENT_FILE_ENDINGS, INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR, \
    BETA_INTEGRATIONS_DIR, INTEGRATION_PREFIX, SCRIPT_PREFIX, PREFIX_TO_ENTITY


class ContentSynchronizer:
    """TODO: add docs, add logging
    """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False):
        self.path = input
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)
        self.custom_content_temp_dir = mkdtemp()
        self.temp_dirs = list()
        self.custom_content = {entity: list() for entity in CONTENT_ENTITIES_DIRS}
        self.pack_content = {entity: list() for entity in CONTENT_ENTITIES_DIRS}
        self.SPECIAL_ENTITIES = {
            TEST_PLAYBOOKS_DIR: PLAYBOOKS_DIR,
            BETA_INTEGRATIONS_DIR: INTEGRATIONS_DIR
        }

    def sync(self) -> int:
        """TODO: might need to implement light mode, just on needed files, add logging
        Syncs downloaded data from demisto to content repository
        """
        self.verify_path_is_pack()
        self.build_pack_content()
        self.fetch_custom_content()
        self.build_custom_content()
        self.merge_to_content_repo()
        self.remove_traces()
        return 0

    def verify_path_is_pack(self) -> None:
        """TODO: add unit test, implement, add logging
        Verifies the input path entered by the user is an actual pack path in content repository
        """
        pass

    def build_pack_content(self) -> None:
        """TODO: add docs, add unit test, add logging
        """
        for content_entity_path in get_child_directories(self.path):
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
        entity_instance_name: str = os.path.basename(remove_trailing_backslash(entity_instance_path))
        content_object: dict = {entity_instance_name: list()}
        main_id, main_data, main_file_path = self.get_main_file_details(content_entity, entity_instance_path)

        for file_path in file_paths:
            content_object[entity_instance_name].append({
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
        main_id: str = str()
        main_file_data: dict = dict()
        main_file_path: str = str()

        # Entities which contain yml files
        if content_entity in (INTEGRATIONS_DIR, BETA_INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR):
            if os.path.isdir(entity_instance_path):
                _, main_file_path = get_yml_paths_in_dir(entity_instance_path)
            elif os.path.isfile(entity_instance_path):
                main_file_path = entity_instance_path

            main_file_data = get_yaml(main_file_path)
            main_id = get_id_by_content_entity(main_file_data, content_entity)

        # Entities which are json files (md files are ignored)
        else:
            if os.path.isfile(entity_instance_path) and entity_instance_path.endswith('json'):
                main_file_path = entity_instance_path
                main_file_data = get_json(entity_instance_path)
                main_id = get_id_by_content_entity(main_file_data, content_entity)

        return main_id, main_file_data, main_file_path

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
                _, temp_file = mkstemp(dir=self.custom_content_temp_dir, prefix=f'{file_name}###')
                with open(temp_file, 'w') as f:
                    f.write(tar.extractfile(member).read().decode('utf-8'))

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
        """TODO: add docs, add unit test, add logging
        """
        files_paths: list = get_files_in_dir(self.custom_content_temp_dir, CUSTOM_CONTENT_FILE_ENDINGS, recursive=False)
        for file_path in files_paths:
            for content_prefix in CONTENT_PREFIXES:
                if content_prefix in file_path:
                    custom_content_object: dict = self.build_custom_content_object(file_path, content_prefix)
                    self.custom_content[content_prefix].append(custom_content_object)

    def build_custom_content_object(self, file_path: str, content_prefix: str) -> dict:
        """TODO: add docs, add unit test, extract to temp_dir, add logging
        """
        artificial_file_path: str = remove_trailing_backslash(file_path).split('###')[0]
        module_name: str = retrieve_module_from_file(artificial_file_path, content_prefix)
        custom_content_object: dict = {module_name: list()}
        content_entity: str = PREFIX_TO_ENTITY[content_prefix]

        if content_prefix in (INTEGRATION_PREFIX, SCRIPT_PREFIX):
            temp_dir = mkdtemp()
            self.temp_dirs.append(temp_dir)
            # extract integration/script here - No Pipfile, Pipfile.lock, README.md, CHANGELOG.md
            extractor = Extractor(input=file_path, output=temp_dir, file_type=content_prefix, base_name=module_name,
                                  no_demisto_mock=True, no_common_server=True, no_auto_create_dir=True, no_readme=True,
                                  no_pipenv=True, no_changelog=True, no_logging=True)
            extractor.extract_to_package_format()
            main_id, _, _ = self.get_main_file_details(content_entity, temp_dir)
            file_paths = get_child_files(temp_dir)
        else:
            file_paths = [file_path]
            main_id, _, _ = self.get_main_file_details(content_entity, file_path)

        for file_path in file_paths:
            file_ending: str = retrieve_file_ending(file_path)
            custom_content_object[module_name].append({
                'id': main_id,
                'path': file_path,
                'data': get_file_data(file_path, file_ending),
                'file_ending': file_ending
            })

        return custom_content_object

    def merge_to_content_repo(self) -> None:
        """TODO: add docs, add unit test, implement, add logging
        """
        pass

    def remove_traces(self):
        """TODO: add unit test, add logging
        Removes (recursively) all temporary files & directories used across the module
        """
        for temp_dir_path in self.temp_dirs + self.custom_content_temp_dir:
            shutil.rmtree(temp_dir_path, ignore_errors=True)

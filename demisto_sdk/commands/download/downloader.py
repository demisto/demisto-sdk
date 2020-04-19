import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from tempfile import mkdtemp
import tarfile
import os
import ast
import io
import shutil
import json
from ruamel.yaml import YAML
from mergedeep import merge
from dictor import dictor
from flatten_dict import unflatten
from tabulate import tabulate

from demisto_sdk.commands.common.tools import get_files_in_dir, get_child_directories, get_yml_paths_in_dir, \
    get_id_by_content_entity, get_yaml, get_child_files, get_json, get_name_by_content_entity, depth, arg_to_list, \
    retrieve_file_ending, get_dict_from_file, find_type, print_color, LOG_COLORS
from demisto_sdk.commands.split_yml.extractor import Extractor
from demisto_sdk.commands.common.constants import CONTENT_ENTITIES_DIRS, CONTENT_FILE_ENDINGS, ENTITY_NAME_SEPARATORS, \
    INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR, BETA_INTEGRATIONS_DIR, ENTITY_TYPE_TO_DIR, \
    DELETED_YML_FIELDS_BY_DEMISTO, DELETED_JSON_FIELDS_BY_DEMISTO


class Downloader:
    """
    Downloader is a class that's designed to merge custom content from Demisto to the content repository.

    Attributes:
        output_pack_path (str): The path of the output pack to download custom content to
        input_files (list): The list of custom content files names to download
        insecure (bool): Indicates whether to you insecure connection or not
        force (bool): Indicates whether to merge existing files or not
        log_verbose (bool): Indicates whether to use verbose logs or not
        client (Demisto client): The Demisto client to make API calls
        custom_content_temp_dir (dir): The temporary dir to store custom content
        temp_dirs (list): A list of all temp dirs used across the module
        files_not_downloaded (list): A list of all files didn't succeeded to be downloaded
        custom_content (list): A list of all custom content objects
        pack_content (dict): The pack content that maps the pack
        SPECIAL_ENTITIES (dict): Used to treat Test Playbook & Beta Integrations as regular entities
    """

    def __init__(self, output: str, input: str, force: bool = False, insecure: bool = False, verbose: bool = False):
        self.output_pack_path = output
        self.input_files = arg_to_list(input)
        self.force = force
        self.insecure = insecure
        self.log_verbose = verbose
        self.client = None
        self.custom_content_temp_dir = mkdtemp()
        self.files_not_downloaded = list()
        self.custom_content = list()
        self.ryaml = YAML()
        self.ryaml.preserve_quotes = True
        self.pack_content = {entity: list() for entity in CONTENT_ENTITIES_DIRS}
        self.SPECIAL_ENTITIES = {TEST_PLAYBOOKS_DIR: PLAYBOOKS_DIR, BETA_INTEGRATIONS_DIR: INTEGRATIONS_DIR}

    def download(self) -> int:
        """
        Downloads custom content data from Demisto to the output pack in content repository.
        """
        if not self.verify_path_is_pack():
            return 1
        self.build_pack_content()
        self.fetch_custom_content()
        self.build_custom_content()
        self.update_pack_hierarchy()
        self.merge_into_pack()
        self.remove_traces()
        self.log_files_not_downloaded()
        return 0

    def verify_path_is_pack(self) -> bool:
        """
        Verifies the output path entered by the user is an actual pack path in content repository.
        :return: Boolean indicates whether the path is pack path or not
        """
        output_pack_path = self.output_pack_path
        if not (os.path.isdir(output_pack_path)
                and os.path.basename(os.path.dirname(os.path.abspath(output_pack_path))) == 'Packs'
                and os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(output_pack_path)))) == 'content'):
            print_color('path is not a pack', LOG_COLORS.RED)
            return False
        return True

    def build_pack_content(self) -> None:
        """TODO: add unit test
        Build the pack content that maps entirely all entity instances within the output pack.
        """
        for content_entity_path in get_child_directories(self.output_pack_path):
            raw_content_entity: str = os.path.basename(os.path.normpath(content_entity_path))
            content_entity: str = self.SPECIAL_ENTITIES.get(raw_content_entity, raw_content_entity)
            child_dirs: list = get_child_directories(content_entity_path)
            # If entity is of type integration/script it will have dirs, else files
            entity_instances_paths: list = child_dirs if child_dirs else get_child_files(content_entity_path)
            for entity_instance_path in entity_instances_paths:
                content_object: dict = self.build_pack_content_object(content_entity, entity_instance_path)
                if content_object:
                    self.pack_content[content_entity].append(content_object)

    def build_pack_content_object(self, content_entity: str, entity_instance_path: str) -> dict:
        """
        Build the pack content object the represents an entity instance.
        For example: HelloWorld Integration in Packs/HelloWorld.
        """
        file_paths: list = get_files_in_dir(entity_instance_path, CONTENT_FILE_ENDINGS, recursive=False)
        # In pack if it's integration/script all the files under it should have the main details of the yml file,
        # else we'll use the file's details.
        content_object: dict = dict()

        if file_paths:
            main_id, main_name = self.get_main_file_details(content_entity, entity_instance_path)
            if main_id and main_name:
                content_object = {main_name: list()}

                for file_path in file_paths:
                    content_object[main_name].append({
                        'name': main_name,
                        'id': main_id,
                        'path': file_path,
                        'file_ending': retrieve_file_ending(file_path)
                    })

        return content_object

    @staticmethod
    def get_main_file_details(content_entity: str, entity_instance_path: str) -> tuple:
        """
        Returns the details of the "main" file within an entity instance.
        For example: In the HelloWorld integration under Packs/HelloWorld, the main file is the yml file.
        It contains all relevant ids and names for all the files under the HelloWorld integration dir.
        """
        main_file_data: dict = dict()
        main_file_path: str = str()

        # Entities which contain yml files
        if content_entity in (INTEGRATIONS_DIR, BETA_INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR):
            if os.path.isdir(entity_instance_path):
                _, main_file_path = get_yml_paths_in_dir(entity_instance_path)
            elif os.path.isfile(entity_instance_path):
                main_file_path = entity_instance_path

            if main_file_path:
                main_file_data = get_yaml(main_file_path)

        # Entities which are json files (md files are ignored - changelog/readme)
        else:
            if os.path.isfile(entity_instance_path) and entity_instance_path.endswith('.json'):
                main_file_data = get_json(entity_instance_path)

        main_id = get_id_by_content_entity(main_file_data, content_entity)
        main_name = get_name_by_content_entity(main_file_data, content_entity)

        return main_id, main_name

    def fetch_custom_content(self) -> None:
        """
        Fetches the custom content from Demisto into a temporary dir.
        """
        self.client = demisto_client.configure(verify_ssl=not self.insecure)
        try:
            api_response: tuple = demisto_client.generic_request_func(self.client, '/content/bundle', 'GET')
            body: bytes = ast.literal_eval(api_response[0])
            io_bytes = io.BytesIO(body)
            # Demisto's custom content file is of type tar.gz
            tar = tarfile.open(fileobj=io_bytes, mode='r')

            for member in tar.getmembers():
                file_name: str = self.update_file_prefix(member.name.strip('/'))
                with open(os.path.join(self.custom_content_temp_dir, file_name), 'w') as file:
                    file.write(tar.extractfile(member).read().decode('utf-8'))

            print_color('\nDownloaded custom content from Demisto server.\n', LOG_COLORS.NATIVE)

        except ApiException as e:
            print(f'Exception raised when fetching custom content: {e}')

    @staticmethod
    def update_file_prefix(file_name: str) -> str:
        """
        Custom content scripts are prefixed with automation instead of script.
        """
        if file_name.startswith('automation-'):
            return file_name.replace('automation-', 'script-')
        return file_name

    def build_custom_content(self) -> None:
        """TODO: add unit test
        Build the custom content that maps entirely all custom content entity instances downloaded from Demisto.
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
                            # move into function
                    custom_content_object['exist_in_pack'] = exist_in_pack
                    self.custom_content.append(custom_content_object)

    @staticmethod
    def build_custom_content_object(file_path: str) -> dict:
        """
        Build the custom content object represents a custom content entity instance.
        For example: integration-HelloWorld.yml downloaded from Demisto.
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
        }

    def update_pack_hierarchy(self) -> None:
        """TODO: add unit test
        Adds all entity dirs (For example: Scripts) are missing.
        Adds all entity instance dirs (For example: HelloWorldScript) are missing.
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
        """
        Creates the dir name corresponding to the file name.
        For example: file_name = Hello World Script, dir_name = HelloWorldScript.
        :param file_name: The file name
        :return: The dir name corresponding to the file name
        """
        dir_name: str = file_name
        for separator in ENTITY_NAME_SEPARATORS:
            dir_name = dir_name.replace(separator, '')
        return dir_name

    def merge_into_pack(self) -> None:
        """
        Merges the custom content into the output pack.
        If force flag is off than will merge only new files, otherwise will "Smart" merge existing files and
        download new files.
        If the custom content entity instance is an integration/script an extraction will be made and the
        relevant files will be merged into the pack.
        yml/json existing files are being "Smart" merged - keeping the important fields deleted by Demisto.
        """
        for custom_content_object in self.custom_content:

            file_entity: str = custom_content_object['entity']
            exist_in_pack: bool = custom_content_object['exist_in_pack']
            file_name: str = custom_content_object['name']
            file_ending: str = custom_content_object['file_ending']
            file_type: str = custom_content_object['type']

            if exist_in_pack:
                if self.force:
                    if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                        # change old to exist
                        self.merge_and_extract_old_file(custom_content_object)
                    elif file_entity == PLAYBOOKS_DIR:
                        # delete
                        self.merge_old_file(custom_content_object, file_ending)
                    else:
                        self.merge_old_file(custom_content_object, file_ending)
                else:
                    self.files_not_downloaded.append([file_name, 'File exists and -f is off'])
                    print_color(f'- Could not merge {file_type} "{file_name}" since file already exists and force flag '
                                f'is off. To merge existing files use the download command with -f.', LOG_COLORS.NATIVE)
            else:
                if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                    self.merge_and_extract_new_file(custom_content_object)
                else:
                    self.merge_new_file(custom_content_object)

    def merge_and_extract_old_file(self, custom_content_object: dict) -> None:
        """TODO: add unit test
        "Smart" merges old files of type integration/script (existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :return: None
        """
        file_path: str = custom_content_object['path']
        file_name: str = custom_content_object['name']
        file_type: str = custom_content_object['type']
        base_name: str = self.create_dir_name(file_name)

        temp_dir = mkdtemp()

        extractor = Extractor(input=file_path, output=temp_dir, file_type=file_type, base_name=base_name,
                              no_logging=True, no_changelog=True, no_pipenv=True, no_readme=True,
                              no_auto_create_dir=True)
        extractor.extract_to_package_format()

        extracted_file_paths: list = get_child_files(temp_dir)
        corresponding_pack_object: dict = self.get_corresponding_pack_content_object(custom_content_object)

        for ex_file_path in extracted_file_paths:
            ex_file_ending: str = retrieve_file_ending(ex_file_path)
            ex_file_detail: str = self.get_extracted_file_detail(ex_file_ending)
            # Get the file name to search for in the pack object (integration/script contains several files of the
            # same type. For example: integration's py code and integration's unit tests code)
            searched_basename: str = self.get_searched_basename(file_name, ex_file_ending, ex_file_detail)
            corresponding_pack_file_object: dict = self.get_corresponding_pack_file_object(searched_basename,
                                                                                           corresponding_pack_object)
            corresponding_pack_file_path: str = corresponding_pack_file_object['path']
            # We use "smart" merge only for yml files (py, png & md files to be moved regularly)
            if ex_file_ending == 'yml':
                self.update_data(ex_file_path, corresponding_pack_file_path, ex_file_ending)
            shutil.move(src=ex_file_path, dst=corresponding_pack_file_path)

        shutil.rmtree(temp_dir)
        print_color(f'- Merged {file_type} "{file_name}"', LOG_COLORS.NATIVE)

    def merge_old_file(self, custom_content_object: dict, file_ending: str) -> None:
        """TODO: add unit test
        "Smart" merges old files of type playbook/json (existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :param file_ending: The file ending
        :return: None
        """
        file_path: str = custom_content_object['path']
        file_name: str = custom_content_object['name']
        file_type: str = custom_content_object['type']

        corresponding_pack_object: dict = self.get_corresponding_pack_content_object(custom_content_object)
        # The corresponding_pack_object will have a list of length 1 as value if it's an old file which isn't
        # integration or script
        corresponding_pack_file_object: dict = corresponding_pack_object[file_name][0]
        corresponding_pack_file_path: str = corresponding_pack_file_object['path']
        self.update_data(file_path, corresponding_pack_file_path, file_ending)
        shutil.move(file_path, corresponding_pack_file_path)

        print_color(f'- Merged {file_type} "{file_name}"', LOG_COLORS.NATIVE)

    def merge_and_extract_new_file(self, custom_content_object: dict) -> None:
        """
        Merges new files of type integration/script (not existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :return: None
        """
        file_entity: str = custom_content_object['entity']
        file_path: str = custom_content_object['path']
        file_type: str = custom_content_object['type']
        file_name: str = custom_content_object['name']

        output_path: str = os.path.join(self.output_pack_path, file_entity)
        # dir name should be the same as file name without separators mentioned in constants.py
        dir_name: str = self.create_dir_name(file_name)
        output_path: str = os.path.join(output_path, dir_name)

        extractor = Extractor(input=file_path, output=output_path, file_type=file_type, base_name=dir_name,
                              no_auto_create_dir=True, no_logging=True, no_pipenv=True)
        extractor.extract_to_package_format()

        print_color(f'- Added {file_type} "{file_name}"', LOG_COLORS.NATIVE)

    def merge_new_file(self, custom_content_object: dict) -> None:
        """
        Merges new files of type playbook/json (not existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :return: None
        """
        file_entity: str = custom_content_object['entity']
        file_path: str = custom_content_object['path']
        file_type: str = custom_content_object['type']
        file_name: str = custom_content_object['name']

        output_path: str = os.path.join(self.output_pack_path, file_entity)
        output_name: str = os.path.basename(file_path)
        output_path: str = os.path.join(output_path, output_name)
        shutil.move(src=file_path, dst=output_path)

        print_color(f'- Added {file_type} "{file_name}"', LOG_COLORS.NATIVE)

    def get_corresponding_pack_content_object(self, custom_content_object: dict) -> dict:
        """TODO: add unit test
        Returns the corresponding pack content object to the given custom content object
        :param custom_content_object: The custom content object to merge into the pack
        :return: The corresponding pack content object
        """
        file_entity: str = custom_content_object['entity']
        file_name: str = custom_content_object['name']
        pack_entity_instances: list = self.pack_content[file_entity]

        for pack_entity_instance in pack_entity_instances:
            if file_name in pack_entity_instance:
                return pack_entity_instance
        return {}

    @staticmethod
    def get_corresponding_pack_file_object(searched_basename: str, pack_content_object: dict) -> dict:
        """TODO: add unit test
        Searches for the file named searched_basename under the pack content object and returns it
        :param searched_basename: The basename to look for
        :param pack_content_object: The pack content object
        :return: The pack file object
        """
        for _, file_objects in pack_content_object.items():
            for file_object in file_objects:
                if file_object['path'].endswith(searched_basename):
                    return file_object
        return {}

    def update_data(self, file_path: str, corresponding_pack_file_path: str, file_ending: str) -> None:
        """TODO: add unit test
        "Smart" merges the yml/json file with the fields deleted by Demisto when custom content was fetched
        :param file_path: The file path
        :param corresponding_pack_file_path: The corresponding pack file path
        :param file_ending: The file ending
        :return: None
        """
        pack_obj_data, _ = get_dict_from_file(corresponding_pack_file_path)
        fields: list = DELETED_YML_FIELDS_BY_DEMISTO if file_ending == 'yml' else DELETED_JSON_FIELDS_BY_DEMISTO
        preserved_data: dict = unflatten({field: dictor(pack_obj_data, field) for field in fields if
                                          dictor(pack_obj_data, field)}, splitter='dot')

        if file_ending == 'yml':
            with open(file_path, 'r') as yf:
                file_yaml_object = self.ryaml.load(yf)
            merge(file_yaml_object, preserved_data)
            with open(file_path, 'w') as yf:
                self.ryaml.dump(file_yaml_object, yf)

        elif file_ending == 'json':
            file_data: dict = get_json(file_path)
            merge(file_data, preserved_data)
            json_depth: int = depth(file_data)
            with open(file_path, 'w') as jf:
                json.dump(obj=file_data, fp=jf, indent=json_depth)

    @staticmethod
    def get_extracted_file_detail(file_ending: str) -> str:
        """
        Returns the corresponding file detail of the extracted integration/script files
        :param file_ending: The file ending
        :return: The file type
        """
        if file_ending == 'py':
            return 'python'
        elif file_ending == 'md':
            return 'description'
        elif file_ending == 'yml':
            return 'yaml'
        elif file_ending == 'png':
            return 'image'
        return ''

    def get_searched_basename(self, file_name: str, file_ending: str, file_detail: str) -> str:
        """
        Creates the file name to search for in the pack content file object
        :param file_name: The file name
        :param file_ending: The file ending
        :param file_detail: The file type
        :return: The searched basename
        """
        if file_detail in ('python', 'yaml'):
            return f'{self.create_dir_name(file_name)}.{file_ending}'
        # description & image files have the detail within the file name
        else:
            return f'{self.create_dir_name(file_name)}_{file_detail}.{file_ending}'

    def remove_traces(self):
        """
        Removes (recursively) all temporary files & directories used across the module
        """
        shutil.rmtree(self.custom_content_temp_dir, ignore_errors=True)

    def log_files_not_downloaded(self) -> None:
        """TODO: add unit test
        Keeps in the not downloaded files list the files haven't been downloaded
        :return: None
        """
        # Get all files not in custom content
        for file_name in self.input_files:
            exist_in_custom_content: bool = False
            for custom_content_object in self.custom_content:
                if file_name == custom_content_object['name']:
                    exist_in_custom_content = True
            if not exist_in_custom_content:
                self.files_not_downloaded.append([file_name, 'File not in custom content'])

        if self.files_not_downloaded:
            print_color("\nDidn't succeed to download the following files:\n", LOG_COLORS.RED)
            print_color(tabulate(self.files_not_downloaded, headers=['FILE NAME', 'REASON']), LOG_COLORS.RED)

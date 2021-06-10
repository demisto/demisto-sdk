import ast
import io
import json
import logging
import os
import shutil
import tarfile
from tempfile import mkdtemp
from typing import Dict, List

import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (
    CONTENT_ENTITIES_DIRS, CONTENT_FILE_ENDINGS,
    DELETED_JSON_FIELDS_BY_DEMISTO, DELETED_YML_FIELDS_BY_DEMISTO,
    ENTITY_NAME_SEPARATORS, ENTITY_TYPE_TO_DIR, FILE_EXIST_REASON,
    FILE_NOT_IN_CC_REASON, INTEGRATIONS_DIR, PLAYBOOKS_DIR, SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR)
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type,
                                               get_child_directories,
                                               get_child_files, get_code_lang,
                                               get_dict_from_file,
                                               get_entity_id_by_entity_type,
                                               get_entity_name_by_entity_type,
                                               get_files_in_dir, get_json,
                                               get_yaml, get_yml_paths_in_dir,
                                               print_color,
                                               retrieve_file_ending)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.split_yml.extractor import Extractor
from dictor import dictor
from flatten_dict import unflatten
from mergedeep import merge
from ruamel.yaml import YAML
from tabulate import tabulate
from urllib3.exceptions import MaxRetryError


class Downloader:
    """
    Downloader is a class that's designed to download and merge custom content from Demisto to the content repository.

    Attributes:
        output_pack_path (str): The path of the output pack to download custom content to
        input_files (list): The list of custom content files names to download
        force (bool): Indicates whether to merge existing files or not
        insecure (bool): Indicates whether to use insecure connection or not
        log_verbose (bool): Indicates whether to use verbose logs or not
        client (Demisto client): The Demisto client to make API calls
        list_files (bool): Indicates whether to print the list of available custom content files and exit or not
        all_custom_content (bool): Indicates whether to download all available custom content or not
        run_format (bool): Indicates whether to run demisto-sdk format on downloaded files or not
        custom_content_temp_dir (dir): The temporary dir to store custom content
        files_not_downloaded (list): A list of all files didn't succeeded to be downloaded
        custom_content (list): A list of all custom content objects
        pack_content (dict): The pack content that maps the pack
    """

    def __init__(self, output: str, input: str, force: bool = False, insecure: bool = False, verbose: bool = False,
                 list_files: bool = False, all_custom_content: bool = False, run_format: bool = False):
        logging.disable(logging.CRITICAL)
        self.output_pack_path = output
        self.input_files = list(input)
        self.force = force
        self.insecure = insecure
        self.log_verbose = verbose
        self.list_files = list_files
        self.all_custom_content = all_custom_content
        self.run_format = run_format
        self.client = None
        self.custom_content_temp_dir = mkdtemp()
        self.all_custom_content_objects: List[dict] = list()
        self.files_not_downloaded: List[list] = list()
        self.custom_content: List[dict] = list()
        self.pack_content: Dict[str, list] = {entity: list() for entity in CONTENT_ENTITIES_DIRS}
        self.num_merged_files = 0
        self.num_added_files = 0

    def download(self) -> int:
        """
        Downloads custom content data from Demisto to the output pack in content repository.
        :return: The exit code
        """
        exit_code: int = self.download_manager()
        self.remove_traces()
        return exit_code

    def download_manager(self) -> int:
        """
        Manages all download command flows
        :return The exit code of each flow
        """
        if not self.verify_flags():
            return 1
        if not self.fetch_custom_content():
            return 1
        if self.handle_list_files_flag():
            return 0
        self.handle_all_custom_content_flag()
        if not self.verify_output_pack_is_pack():
            return 1

        self.build_pack_content()
        self.build_custom_content()
        self.update_pack_hierarchy()
        self.merge_into_pack()
        self.log_files_downloaded()
        self.log_files_not_downloaded()

        if self.files_not_downloaded:
            return 1

        return 0

    def verify_flags(self) -> bool:
        """
        Verifies that the flags configuration given by the user is correct
        :return: The verification result
        """
        if not self.list_files:
            output_flag, input_flag = True, True
            if not self.output_pack_path:
                output_flag = False
                print_color("Error: Missing option '-o' / '--output'.", LOG_COLORS.RED)
            if not self.input_files:
                if not self.all_custom_content:
                    input_flag = False
                    print_color("Error: Missing option '-i' / '--input'.", LOG_COLORS.RED)
            if not input_flag or not output_flag:
                return False
        return True

    def fetch_custom_content(self) -> bool:
        """
        Fetches the custom content from Demisto into a temporary dir.
        :return: True if fetched successfully, False otherwise
        """
        try:
            verify = (not self.insecure) if self.insecure else None  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
            self.client = demisto_client.configure(verify_ssl=verify)
            api_response: tuple = demisto_client.generic_request_func(self.client, '/content/bundle', 'GET')
            body: bytes = ast.literal_eval(api_response[0])
            io_bytes = io.BytesIO(body)
            # Demisto's custom content file is of type tar.gz
            tar = tarfile.open(fileobj=io_bytes, mode='r')

            for member in tar.getmembers():
                file_name: str = self.update_file_prefix(member.name.strip('/'))
                file_path: str = os.path.join(self.custom_content_temp_dir, file_name)
                with open(file_path, 'w') as file:
                    extracted_file = tar.extractfile(member)
                    # File might empty
                    if extracted_file:
                        string_to_write = extracted_file.read().decode('utf-8')
                        file.write(string_to_write)
                    else:
                        raise FileNotFoundError(f'Could not extract files from tar file: {file_path}')

            return True

        except ApiException as e:
            if e.status == 401:
                print_color('\nVerify that the environment variable DEMISTO_API_KEY is configured properly.\n',
                            LOG_COLORS.RED)
            print_color(f'Exception raised when fetching custom content:\nStatus: {e}', LOG_COLORS.NATIVE)
            return False
        except MaxRetryError as e:
            print_color('\nVerify that the environment variable DEMISTO_BASE_URL is configured properly.\n',
                        LOG_COLORS.RED)
            print_color(f'Exception raised when fetching custom content:\n{e}', LOG_COLORS.NATIVE)
            return False
        except Exception as e:
            print_color(f'Exception raised when fetching custom content:\n{e}', LOG_COLORS.NATIVE)
            return False

    def get_custom_content_objects(self) -> List[dict]:
        """
        Creates a list of all custom content objects
        :return: The list of all custom content objects
        """
        custom_content_file_paths: list = get_child_files(self.custom_content_temp_dir)
        custom_content_objects: List = list()
        for file_path in custom_content_file_paths:
            custom_content_object: Dict = self.build_custom_content_object(file_path)
            if custom_content_object['type']:
                # If custom content object's type is empty it means the file isn't of support content entity
                custom_content_objects.append(custom_content_object)
        return custom_content_objects

    def handle_list_files_flag(self) -> bool:
        """
        Prints the list of all files available to be downloaded from Demisto Instance
        :return: True if list-files flag is on and listing available files process succeeded, False otherwise
        """
        if self.list_files:
            self.all_custom_content_objects = self.get_custom_content_objects()
            list_files = [[cco['name'], cco['type']] for cco in self.all_custom_content_objects
                          if cco.get('name')]
            print_color('\nThe following files are available to be downloaded from Demisto instance:\n',
                        LOG_COLORS.NATIVE)
            print(tabulate(list_files, headers=['FILE NAME', 'FILE TYPE']))
            return True
        return False

    def handle_all_custom_content_flag(self) -> None:
        """
        Handles the case where the all custom content flag is given
        :return: None
        """
        if self.all_custom_content:
            custom_content_objects: list = self.get_custom_content_objects()
            names_list: list = [cco['name'] for cco in custom_content_objects]
            # Remove duplicated names, for example: IncidentType & Layout with the same name.
            self.input_files = list(set(names_list))

    def verify_output_pack_is_pack(self) -> bool:
        """
        Verifies the output path entered by the user is an actual pack path in content repository.
        :return: The verification result
        """
        output_pack_path = self.output_pack_path
        if not (os.path.isdir(output_pack_path) and
                os.path.basename(os.path.dirname(os.path.abspath(output_pack_path))) == 'Packs'):
            print_color(f"Path {output_pack_path} is not a valid Path pack. The designated output pack's path is"
                        f" of format ~/.../Packs/$PACK_NAME", LOG_COLORS.RED)
            return False
        return True

    def build_pack_content(self) -> None:
        """
        Build a data structure called custom content that holds basic data for each content entity within the given output pack.
        For example check out the PACK_CONTENT variable in downloader_test.py
        """
        for content_entity_path in get_child_directories(self.output_pack_path):
            raw_content_entity: str = os.path.basename(os.path.normpath(content_entity_path))
            content_entity: str = raw_content_entity
            if content_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                # If entity is of type integration/script it will have dirs, otherwise files
                entity_instances_paths: list = get_child_directories(content_entity_path)
            else:
                entity_instances_paths = get_child_files(content_entity_path)
            for entity_instance_path in entity_instances_paths:
                content_object: dict = self.build_pack_content_object(content_entity, entity_instance_path)
                if content_object:
                    self.pack_content[content_entity].append(content_object)

    def build_pack_content_object(self, content_entity: str, entity_instance_path: str) -> dict:
        """
        Build the pack content object the represents an entity instance.
        For example: HelloWorld Integration in Packs/HelloWorld.
        :param content_entity: The content entity, for example Integrations
        :param entity_instance_path: For example, for integration: ~/.../content/Packs/TestPack/Integrations/HelloWorld
        and for layout: ~/.../content/Packs/TestPack/Layout/layout-HelloWorldLayout.json
        :return: A pack content object. For example, INTEGRATION_PACK_OBJECT / LAYOUT_PACK_OBJECT variables
        in downloader_test.py
        """
        # If the entity_instance_path is a file then get_files_in_dir will return the list: [entity_instance_path]
        file_paths: list = get_files_in_dir(entity_instance_path, CONTENT_FILE_ENDINGS, recursive=False)
        # If it's integration/script, all files under it should have the main details of the yml file,
        # otherwise we'll use the file's details.
        content_object: dict = dict()
        main_id, main_name = self.get_main_file_details(content_entity, entity_instance_path)
        # if main file doesn't exist/no entity instance path exist the content object won't be added to the pack content
        if all((main_id, main_name, file_paths)):
            content_object = {main_name: list()}
            # For example take a look at INTEGRATION_CUSTOM_CONTENT_OBJECT variable in downloader_test.py

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
        :param content_entity: The content entity, for example Integrations
        :param entity_instance_path: For example: ~/.../content/Packs/TestPack/Integrations/HelloWorld
        :return: The main file id & name
        """
        main_file_data: dict = dict()
        main_file_path: str = str()

        # Entities which contain yml files
        if content_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR, PLAYBOOKS_DIR, TEST_PLAYBOOKS_DIR):
            if os.path.isdir(entity_instance_path):
                _, main_file_path = get_yml_paths_in_dir(entity_instance_path)
            elif os.path.isfile(entity_instance_path):
                main_file_path = entity_instance_path

            if main_file_path:
                main_file_data = get_yaml(main_file_path)

        # Entities which are json files (md files are ignored - changelog/readme)
        else:
            if os.path.isfile(entity_instance_path) and retrieve_file_ending(entity_instance_path) == 'json':
                main_file_data = get_json(entity_instance_path)

        main_id = get_entity_id_by_entity_type(main_file_data, content_entity)
        main_name = get_entity_name_by_entity_type(main_file_data, content_entity)

        return main_id, main_name

    @staticmethod
    def update_file_prefix(file_name: str) -> str:
        """
        Custom content scripts are prefixed with automation instead of script.
        Removing the "playbook-" prefix from files name.
        """
        if file_name.startswith('playbook-'):
            return file_name[len('playbook-'):]
        if file_name.startswith('automation-'):
            return file_name.replace('automation-', 'script-')
        return file_name

    def build_custom_content(self) -> None:
        """
        Build a data structure called pack content that holds basic data for each content entity instances downloaded from Demisto.
        For example check out the CUSTOM_CONTENT variable in downloader_test.py
        """
        custom_content_objects = self.all_custom_content_objects if self.all_custom_content_objects else\
            self.get_custom_content_objects()
        for input_file_name in self.input_files:
            input_file_exist_in_cc: bool = False
            for custom_content_object in custom_content_objects:
                name = custom_content_object.get('name', 'N/A')
                if name == input_file_name:
                    custom_content_object['exist_in_pack'] = self.exist_in_pack_content(custom_content_object)
                    self.custom_content.append(custom_content_object)
                    input_file_exist_in_cc = True
            # If in input files and not in custom content files
            if not input_file_exist_in_cc:
                self.files_not_downloaded.append([input_file_name, FILE_NOT_IN_CC_REASON])

        number_of_files = len(self.custom_content)
        print_color(f'\nDemisto instance: Enumerating objects: {number_of_files}, done.',
                    LOG_COLORS.NATIVE)
        print_color(f'Demisto instance: Receiving objects: 100% ({number_of_files}/{number_of_files}),'
                    f' done.\n', LOG_COLORS.NATIVE)

    def exist_in_pack_content(self, custom_content_object: dict) -> bool:
        """
        Checks if the current custom content object already exists in custom content
        :param custom_content_object: The custom content object
        :return: True if exists, False otherwise
        """
        entity: str = custom_content_object['entity']
        name = custom_content_object['name']
        exist_in_pack: bool = False

        for entity_instance_object in self.pack_content[entity]:
            if name in entity_instance_object:
                exist_in_pack = True

        return exist_in_pack

    def build_custom_content_object(self, file_path: str) -> dict:
        """
        Build the custom content object represents a custom content entity instance.
        For example: integration-HelloWorld.yml downloaded from Demisto.
        """
        file_data, file_ending = get_dict_from_file(file_path)  # For example: yml, for integration files
        file_type = find_type(path=file_path, _dict=file_data, file_type=file_ending)  # For example: integration
        if file_type:
            file_type = file_type.value

        file_entity = self.file_type_to_entity(file_data, file_type)  # For example: Integrations
        file_id: str = get_entity_id_by_entity_type(file_data, file_entity)
        file_name: str = get_entity_name_by_entity_type(file_data, file_entity)

        custom_content_object: dict = {
            'id': file_id,
            'name': file_name,
            'path': file_path,
            'entity': file_entity,
            'type': file_type,
            'file_ending': file_ending,
        }

        file_code_language = get_code_lang(file_data, file_entity)
        if file_code_language:
            custom_content_object['code_lang'] = file_code_language

        return custom_content_object

    @staticmethod
    def file_type_to_entity(file_data: dict, file_type: str) -> str:
        """
        Given the file type returns the file entity
        :param file_data: The file data
        :param file_type: The file type, for example: integration
        :return: The file entity, for example: Integrations
        """
        if file_type and file_type == 'playbook':
            name: str = get_entity_name_by_entity_type(file_data, PLAYBOOKS_DIR)
            if name and 'test' in name.lower():
                return TEST_PLAYBOOKS_DIR
        return ENTITY_TYPE_TO_DIR.get(file_type, '')

    def update_pack_hierarchy(self) -> None:
        """
        Adds all entity dirs (For example: Scripts) that are missing.
        Adds all entity instance dirs (For example: HelloWorldScript) that are missing.
        :return: None
        """
        for custom_content_object in self.custom_content:

            file_entity: str = custom_content_object['entity']
            file_name: str = custom_content_object['name']
            entity_path: str = os.path.join(self.output_pack_path, file_entity)

            if not os.path.isdir(entity_path):
                os.mkdir(entity_path)
            # Only integration/script have entity_instance_path which is a dir.
            # For example: ~/.../content/Packs/TestPack/Integrations/HelloWorld
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

    def verify_code_lang(self, code_lang: str, file_type: str, file_name: str) -> bool:
        """
        Verifies the code language of the integration/script is not JavaScript
        :param code_lang: The code language
        :param file_type: The file type
        :param file_name: The file name
        :return: A boolean indicates whether the code language is JavaScript or not
        """
        if not code_lang or code_lang == 'javascript':
            if file_type == 'integration':
                reason = 'Downloading an integration written in JavaScript is not supported.'
                self.files_not_downloaded.append([file_name, reason])
            elif file_type == 'script':
                reason = 'Downloading a script written in JavaScript is not supported.'
                self.files_not_downloaded.append([file_name, reason])
            return False
        return True

    def merge_into_pack(self) -> None:
        """
        Merges the custom content into the output pack.
        For integrations/scripts an extraction will be made and the relevant files will be merged into the pack.
        If force flag is given then the function will add new files and "Smartly" merge existing files such that
        important fields deleted by Demisto will be kept. If no force is present, it will only download new files.
        """
        for custom_content_object in self.custom_content:

            file_entity: str = custom_content_object['entity']  # For example: Integrations
            exist_in_pack: bool = custom_content_object['exist_in_pack']   # For example: True
            file_name: str = custom_content_object['name']   # For example: Hello World
            file_ending: str = custom_content_object['file_ending']   # For example: yml

            if exist_in_pack:
                if self.force:
                    if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                        self.merge_and_extract_existing_file(custom_content_object)
                    else:
                        self.merge_existing_file(custom_content_object, file_ending)
                else:
                    self.files_not_downloaded.append([file_name, FILE_EXIST_REASON])
            else:
                if file_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                    self.merge_and_extract_new_file(custom_content_object)
                else:
                    self.merge_new_file(custom_content_object)

    def merge_and_extract_existing_file(self, custom_content_object: dict) -> None:
        """
        "Smart" merges old files of type integration/script (existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :return: None
        """
        file_path: str = custom_content_object['path']
        file_name: str = custom_content_object['name']
        file_type: str = custom_content_object['type']
        file_entity: str = custom_content_object['entity']

        file_code_language: str = custom_content_object.get('code_lang', '')
        if not self.verify_code_lang(file_code_language, file_type, file_name):
            return

        base_name: str = self.create_dir_name(file_name)
        temp_dir = mkdtemp()

        extractor = Extractor(input=file_path, output=temp_dir, file_type=file_type, base_name=base_name,
                              no_logging=not self.log_verbose, no_pipenv=True, no_readme=True,
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
            if not corresponding_pack_file_object:
                corresponding_pack_file_path: str = os.path.join(self.output_pack_path, file_entity,
                                                                 self.create_dir_name(file_name), searched_basename)
            else:
                corresponding_pack_file_path = corresponding_pack_file_object['path']
            # We use "smart" merge only for yml files (py, png  & md files to be moved regularly)
            if ex_file_ending == 'yml':
                # adding the deleted fields (by Demisto) of the old yml/json file to the custom content file.
                self.update_data(ex_file_path, corresponding_pack_file_path, ex_file_ending)
            try:
                shutil.move(src=ex_file_path, dst=corresponding_pack_file_path)
            except shutil.Error as e:
                print_color(e, LOG_COLORS.RED)
                raise
            self.format_file(corresponding_pack_file_path, ex_file_ending)

        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except shutil.Error as e:
            print_color(e, LOG_COLORS.RED)
            raise

        self.num_merged_files += 1
        self.log_finished_file('Merged', file_name, file_entity[:-1])

    def merge_existing_file(self, custom_content_object: dict, file_ending: str) -> None:
        """
        "Smart" merges the newly downloaded files into the existing files of type PB/json (existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :param file_ending: The file ending
        :return: None
        """
        file_path: str = custom_content_object['path']
        file_name: str = custom_content_object['name']
        file_entity: str = custom_content_object['entity']

        corresponding_pack_object: dict = self.get_corresponding_pack_content_object(custom_content_object)
        # The corresponding_pack_object will have a list of length 1 as value if it's an old file which isn't
        # integration or script
        corresponding_pack_file_object: dict = corresponding_pack_object[file_name][0]
        corresponding_pack_file_path: str = corresponding_pack_file_object['path']
        # adding the deleted fields (by Demisto) of the old yml/json file to the custom content file.
        self.update_data(file_path, corresponding_pack_file_path, file_ending)

        try:
            shutil.move(src=file_path, dst=corresponding_pack_file_path)
        except shutil.Error as e:
            print_color(e, LOG_COLORS.RED)
            raise

        self.format_file(corresponding_pack_file_path, corresponding_pack_file_object['file_ending'])
        self.num_merged_files += 1
        self.log_finished_file('Merged', file_name, file_entity[:-1])

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

        file_code_language: str = custom_content_object.get('code_lang', '')
        if not self.verify_code_lang(file_code_language, file_type, file_name):
            return

        dir_output_path: str = os.path.join(self.output_pack_path, file_entity)
        # dir name should be the same as file name without separators mentioned in constants.py
        dir_name: str = self.create_dir_name(file_name)
        dir_output_path = os.path.join(dir_output_path, dir_name)

        extractor = Extractor(input=file_path, output=dir_output_path, file_type=file_type, base_name=dir_name,
                              no_auto_create_dir=True, no_logging=not self.log_verbose, no_pipenv=True)
        extractor.extract_to_package_format()

        for file_path in get_child_files(dir_output_path):
            self.format_file(file_path, retrieve_file_ending(file_path))
        self.num_added_files += 1
        self.log_finished_file('Added', file_name, file_entity[:-1])

    def merge_new_file(self, custom_content_object: dict) -> None:
        """
        Merges new files of type playbook/json (not existing in the output pack)
        :param custom_content_object: The custom content object to merge into the pack
        :return: None
        """
        file_entity: str = custom_content_object['entity']
        file_path: str = custom_content_object['path']
        file_name: str = custom_content_object['name']
        file_ending: str = custom_content_object['file_ending']

        dir_output_path: str = os.path.join(self.output_pack_path, file_entity)
        file_output_name: str = os.path.basename(file_path)
        file_output_path: str = os.path.join(dir_output_path, file_output_name)
        try:
            shutil.move(src=file_path, dst=file_output_path)
        except shutil.Error as e:
            print_color(e, LOG_COLORS.RED)
            raise

        self.format_file(file_output_path, file_ending)
        self.num_added_files += 1
        self.log_finished_file('Added', file_name, file_entity[:-1])

    def log_finished_file(self, action: str, file_name: str, file_type: str) -> None:
        """
        Logs a message to the user when file download has finished
        :param action: The action has been made (merge/download)
        :param file_name: The file name
        :param file_type: The file type
        :return: None
        """
        print_color(f'- {action} {file_type} "{file_name}"', LOG_COLORS.NATIVE)
        if self.run_format:  # TODO: Refactored after format had verbose arg
            print_color('', LOG_COLORS.NATIVE)

    def get_corresponding_pack_content_object(self, custom_content_object: dict) -> dict:
        """
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
        """
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

    @staticmethod
    def update_data(file_path_to_write: str, file_path_to_read: str, file_ending: str) -> None:
        """
        Collects special chosen fields from the file_path_to_read and writes them into the file_path_to_write.
        :param file_path_to_write: The output file path to add the special fields to.
        :param file_path_to_read: The input file path to read the special fields from.
        :param file_ending: The files ending
        :return: None
        """

        pack_obj_data, _ = get_dict_from_file(file_path_to_read)
        fields: list = DELETED_YML_FIELDS_BY_DEMISTO if file_ending == 'yml' else DELETED_JSON_FIELDS_BY_DEMISTO
        # Creates a nested-complex dict of all fields to be deleted by Demisto.
        # We need the dict to be nested, to easily merge it later to the file data.
        preserved_data: dict = unflatten({field: dictor(pack_obj_data, field) for field in fields if
                                          dictor(pack_obj_data, field)}, splitter='dot')

        if file_ending == 'yml':
            ryaml = YAML()
            ryaml.preserve_quotes = True  # type: ignore
            with open(file_path_to_write, 'r') as yf:
                file_yaml_object = ryaml.load(yf)
            if pack_obj_data:
                merge(file_yaml_object, preserved_data)
            with open(file_path_to_write, 'w') as yf:
                ryaml.dump(file_yaml_object, yf)

        elif file_ending == 'json':
            file_data: dict = get_json(file_path_to_write)
            if pack_obj_data:
                merge(file_data, preserved_data)
            with open(file_path_to_write, 'w') as jf:
                json.dump(obj=file_data, fp=jf, indent=4)

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

    def format_file(self, file_path: str, file_ending: str) -> None:
        """
        Runs demisto-sdk format on the file
        :param file_path: The file path
        :param file_ending: The file ending
        :return: None
        """
        if self.run_format and file_ending in ('yml', 'json'):
            format_manager(input=os.path.abspath(file_path), no_validate=False)

    def remove_traces(self):
        """
        Removes (recursively) all temporary files & directories used across the module
        """
        try:
            shutil.rmtree(self.custom_content_temp_dir, ignore_errors=True)
        except shutil.Error as e:
            print_color(e, LOG_COLORS.RED)
            raise

    def log_files_downloaded(self) -> None:
        """
        Log files downloaded/merged
        :return: None
        """
        log_msg, added_msg, merged_msg = str(), str(), str()
        if self.num_added_files:
            files = 'file' if self.num_added_files == 1 else 'files'
            added_msg = f'{self.num_added_files} {files} added'
        if self.num_merged_files:
            files = 'file' if self.num_merged_files == 1 else 'files'
            merged_msg = f'{self.num_merged_files} {files} merged'
        if added_msg:
            if merged_msg:
                log_msg = f'\n{added_msg}, {merged_msg}.'
            else:
                log_msg = f'\n{added_msg}.'
        elif merged_msg:
            log_msg = f'\n{merged_msg}.'
        if log_msg:
            print_color(log_msg, LOG_COLORS.NATIVE)

    def log_files_not_downloaded(self) -> None:
        """
        Logs a table of all files haven't been downloaded by Demisto
        :return: None
        """
        if self.files_not_downloaded:
            print_color("\nFailed to download the following files:\n", LOG_COLORS.RED)
            print_color(tabulate(self.files_not_downloaded, headers=['FILE NAME', 'REASON']), LOG_COLORS.RED)
            reasons: list = [file[1] for file in self.files_not_downloaded]
            if FILE_EXIST_REASON in reasons:
                print_color('\nTo merge existing files use the download command with -f.', LOG_COLORS.NATIVE)

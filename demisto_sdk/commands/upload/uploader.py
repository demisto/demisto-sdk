import json
import os
from tempfile import NamedTemporaryFile
from typing import List, Tuple

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (CONTENT_ENTITIES_DIRS,
                                                   CONTENT_ENTITY_UPLOAD_ORDER,
                                                   INTEGRATIONS_DIR, PACKS_DIR,
                                                   SCRIPTS_DIR)
from demisto_sdk.commands.common.tools import (
    LOG_COLORS, find_type, get_child_directories, get_child_files, get_json,
    get_parent_directory_name, is_path_of_classifier_directory,
    is_path_of_dashboard_directory, is_path_of_incident_field_directory,
    is_path_of_incident_type_directory, is_path_of_integration_directory,
    is_path_of_layout_directory, is_path_of_playbook_directory,
    is_path_of_script_directory, is_path_of_test_playbook_directory,
    is_path_of_widget_directory, print_color, print_error, print_v)
from demisto_sdk.commands.unify.unifier import Unifier
from tabulate import tabulate


class Uploader:
    """Upload a pack specified in self.infile to a remote Cortex XSOAR instance.
        Attributes:
            path (str): The path of a pack / directory / file to upload.
            verbose (bool): Whether to output a detailed response.
            client (DefaultApi): Demisto-SDK client object.
        """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False):
        self.path = input
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)
        self.status_code = 0
        self.successfully_uploaded_files: List[Tuple[str, str]] = []
        self.failed_uploaded_files: List[Tuple[str, str]] = []

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance.
        """
        print(f"Uploading {self.path} ...")
        parent_dir_name = get_parent_directory_name(self.path)

        if not os.path.exists(self.path):
            print_error(f'Error: Given input path: {self.path} does not exist')
            self.status_code = 1

        # Input is a file
        elif os.path.isfile(self.path):
            file_type = find_type(self.path)
            if file_type == 'integration':
                self.integration_uploader(self.path)
            elif file_type == 'script':
                self.script_uploader(self.path)
            elif file_type == 'playbook':
                self.playbook_uploader(self.path)
            elif file_type == 'widget':
                self.widget_uploader(self.path)
            elif file_type == 'incidenttype':
                self.incident_type_uploader(self.path)
            elif file_type == 'classifier':
                self.classifier_uploader(self.path)
            elif file_type == 'classifier_5_9_9':
                self.classifier_uploader(self.path)
            elif file_type == 'layout':
                self.layout_uploader(self.path)
            elif file_type == 'dashboard':
                self.dashboard_uploader(self.path)
            elif file_type == 'incidentfield':
                self.incident_field_uploader(self.path)
            else:
                print_error(
                    f'\nError: Given input path: {self.path} is not valid. '
                    f'Input path should point to one of the following:\n'
                    f'  1. Pack\n'
                    f'  2. A content entity directory that is inside a pack. For example: an Integrations directory or '
                    f'a Layouts directory\n'
                    f'  3. Valid file that can be imported to Cortex XSOAR manually. '
                    f'For example a playbook: helloWorld.yml'
                )
                self.status_code = 1

        elif os.path.isdir(self.path):
            # Input is an integration directory (HelloWorld)
            if parent_dir_name == INTEGRATIONS_DIR:
                self.integration_uploader(self.path)

            # Input is a script directory (commonServerPython)
            elif parent_dir_name == SCRIPTS_DIR:
                self.script_uploader(self.path)

            # Input is a content entity directory (Integrations/Scripts/Playbook etc...)
            elif os.path.basename(self.path) in CONTENT_ENTITIES_DIRS:
                self.directory_uploader(self.path)

            # Input is a pack
            elif parent_dir_name == PACKS_DIR:
                self.pack_uploader()

            # Input is not supported
            else:
                print_error(
                    f'\nError: Given input path: {self.path} is not valid. '
                    f'Input path should point to one of the following:\n'
                    f'  1. Pack\n'
                    f'  2. A content entity directory that is inside a pack. For example: an Integrations directory or '
                    f'a Layouts directory\n'
                    f'  3. Valid file that can be imported to Cortex XSOAR manually. '
                    f'For example a playbook: helloWorld.yml'
                )
                self.status_code = 1

        self._print_summary()
        return self.status_code

    def pack_uploader(self):
        """Extracts the directories of the pack and upload them by directory_uploader
        """
        list_directories = get_child_directories(self.path)
        ordered_directories_list = self._sort_directories_based_on_dependencies(list_directories)
        for directory in ordered_directories_list:
            self.directory_uploader(directory)

    def directory_uploader(self, path: str):
        """Uploads directories by path

        Args:
            path (str): Path for directory to upload.
        """
        if is_path_of_integration_directory(path):
            list_integrations = get_child_directories(path)
            for integration in list_integrations:
                self.integration_uploader(integration)

        elif is_path_of_script_directory(path):
            list_script = get_child_directories(path)
            for script in list_script:
                self.script_uploader(script)

        elif is_path_of_playbook_directory(path) or is_path_of_test_playbook_directory(path):
            list_playbooks = get_child_files(path)
            for playbook in list_playbooks:
                if playbook.endswith('.yml'):
                    self.playbook_uploader(playbook)

        elif is_path_of_incident_field_directory(path):
            list_incident_fields = get_child_files(path)
            for incident_field in list_incident_fields:
                if incident_field.endswith('.json'):
                    self.incident_field_uploader(incident_field)

        elif is_path_of_widget_directory(path):
            list_widgets = get_child_files(path)
            for widget in list_widgets:
                if widget.endswith('.json'):
                    self.widget_uploader(widget)

        elif is_path_of_dashboard_directory(path):
            list_dashboards = get_child_files(path)
            for dashboard in list_dashboards:
                if dashboard.endswith('.json'):
                    self.dashboard_uploader(dashboard)

        elif is_path_of_layout_directory(path):
            list_layouts = get_child_files(path)
            for layout in list_layouts:
                if layout.endswith('.json'):
                    self.layout_uploader(layout)

        elif is_path_of_incident_type_directory(path):
            list_incident_types = get_child_files(path)
            for incident_type in list_incident_types:
                if incident_type.endswith('.json'):
                    self.incident_type_uploader(incident_type)

        elif is_path_of_classifier_directory(path):
            list_classifiers = get_child_files(path)
            for classifiers in list_classifiers:
                if classifiers.endswith('.json'):
                    self.classifier_uploader(classifiers)

    def integration_uploader(self, path: str):
        is_dir = False
        file_name = os.path.basename(path)
        docker45_path = ''

        try:
            if os.path.isdir(path):  # Create a temporary unified yml file
                try:
                    is_dir = True
                    unifier = Unifier(input=path, output=path)
                    unified_paths = unifier.merge_script_package_to_yml()
                    path = unified_paths[0]
                    docker45_path = unified_paths[1] if len(unified_paths) > 1 else ''
                    file_name = os.path.basename(path)
                except IndexError:
                    print_error(f'Error uploading integration from pack. /'
                                f'Check that the given integration path contains a valid integration: {path}.')

                    self.status_code = 1
                    self.failed_uploaded_files.append((file_name, 'Integration'))
                    return

                except Exception as err:
                    print_error(str('Upload integration failed\n'))
                    print_error(str(err))
                    self.failed_uploaded_files.append((file_name, 'Integration'))
                    self.status_code = 1
                    return

            # Upload the file to Cortex XSOAR
            result = self.client.integration_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded integration - \'{file_name}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Integration'))

        except Exception as err:
            self._parse_error_response(err, 'integration', file_name)
            self.failed_uploaded_files.append((file_name, 'Integration'))
            self.status_code = 1

        finally:
            # Remove the temporary file
            if is_dir:
                self._remove_temp_file(path)
                if docker45_path:
                    self._remove_temp_file(docker45_path)

    def script_uploader(self, path: str):
        is_dir = False
        file_name = os.path.basename(path)
        docker45_path = ''

        try:
            if os.path.isdir(path):  # Create a temporary unified yml file
                is_dir = True
                try:
                    unifier = Unifier(input=path, output=path)
                    unified_paths = unifier.merge_script_package_to_yml()
                    path = unified_paths[0]
                    docker45_path = unified_paths[1] if len(unified_paths) > 1 else ''
                    file_name = os.path.basename(path)
                except IndexError:
                    print_error(f'Error uploading script from pack. /'
                                f'Check that the given script path contains a valid script: {path}.')
                    self.status_code = 1
                    self.failed_uploaded_files.append((file_name, 'Script'))
                    return

                except Exception as err:
                    print_error(str('Upload script failed\n'))
                    print_error(str(err))
                    self.status_code = 1
                    self.failed_uploaded_files.append((file_name, 'Script'))
                    return

            # Upload the file to Cortex XSOAR
            result = self.client.import_script(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded script - \'{file_name}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Script'))

        except Exception as err:
            self._parse_error_response(err, 'script', file_name)
            self.failed_uploaded_files.append((file_name, 'Script'))
            self.status_code = 1

        finally:
            # Remove the temporary file
            if is_dir:
                self._remove_temp_file(path)
                if docker45_path:
                    self._remove_temp_file(docker45_path)

    def playbook_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Upload the file to Cortex XSOAR
            result = self.client.import_playbook(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded playbook - \'{file_name}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Playbook'))

        except Exception as err:
            self._parse_error_response(err, 'playbook', file_name)
            self.failed_uploaded_files.append((file_name, 'Playbook'))
            self.status_code = 1

    def incident_field_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Wrap the incident object with a list to be compatible with Cortex XSOAR
            incident_fields_unified_data = {'incidentFields': [get_json(path)]}
            # Create a temp file object
            incidents_unified_file = NamedTemporaryFile(dir=f'{os.path.dirname(path)}', suffix='.json', delete=False)
            incidents_unified_file.write(bytes(json.dumps(incident_fields_unified_data), 'utf-8'))
            new_file_path = incidents_unified_file.name
            incidents_unified_file.close()

            # Upload the file to Cortex XSOAR
            result = self.client.import_incident_fields(file=new_file_path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded incident field - \'{os.path.basename(path)}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Incident Field'))

        except Exception as err:
            self._parse_error_response(err, 'incident field', file_name)
            self.failed_uploaded_files.append((file_name, 'Incident Field'))
            self.status_code = 1

        finally:
            self._remove_temp_file(new_file_path)

    def widget_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Upload the file to Cortex XSOAR
            result = self.client.import_widget(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded widget - \'{os.path.basename(path)}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Widget'))

        except Exception as err:
            self._parse_error_response(err, 'widget', file_name)
            self.failed_uploaded_files.append((file_name, 'Widget'))
            self.status_code = 1

    def dashboard_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Upload the file to Cortex XSOAR
            result = self.client.import_dashboard(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded dashboard - \'{os.path.basename(path)}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Dashboard'))

        except Exception as err:
            self._parse_error_response(err, 'dashboard', file_name)
            self.failed_uploaded_files.append((file_name, 'Dashboard'))
            self.status_code = 1

    def layout_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Upload the file to Cortex XSOAR
            result = self.client.import_layout(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded layout - \'{os.path.basename(path)}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Layout'))

        except Exception as err:
            self._parse_error_response(err, 'layout', file_name)
            self.failed_uploaded_files.append((file_name, 'Layout'))
            self.status_code = 1

    def incident_type_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Wrap the incident object with a list to be compatible with Cortex XSOAR
            incident_types_unified_data = [get_json(path)]
            # Create a temp file object
            incidents_unified_file = NamedTemporaryFile(dir=f'{os.path.dirname(path)}', suffix='.json', delete=False)
            incidents_unified_file.write(bytes(json.dumps(incident_types_unified_data), 'utf-8'))
            new_file_path = incidents_unified_file.name
            incidents_unified_file.close()

            # Upload the file to Cortex XSOAR
            result = self.client.import_incident_types_handler(file=new_file_path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded incident type - \'{os.path.basename(path)}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Incident Type'))

        except Exception as err:
            self._parse_error_response(err, 'incident type', file_name)
            self.failed_uploaded_files.append((file_name, 'Incident Type'))
            self.status_code = 1

        finally:
            self._remove_temp_file(new_file_path)

    def classifier_uploader(self, path: str):
        file_name = os.path.basename(path)

        try:
            # Upload the file to Cortex XSOAR
            result = self.client.import_classifier(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded classifier - \'{os.path.basename(path)}\': successfully', LOG_COLORS.GREEN)
            self.successfully_uploaded_files.append((file_name, 'Classifier'))
        except Exception as err:
            self._parse_error_response(err, 'classifier', file_name)
            self.failed_uploaded_files.append((file_name, 'Classifier'))
            self.status_code = 1

    def _parse_error_response(self, error: ApiException, file_type: str, file_name: str):
        """Parses error message from exception raised in call to client to upload a file

        error (ApiException): The exception which was raised in call in to client
        file_type (str): The file type which was attempted to be uploaded
        file_name (str): The file name which was attempted to be uploaded
        """
        message = error
        if hasattr(error, 'reason'):
            if '[SSL: CERTIFICATE_VERIFY_FAILED]' in str(error.reason):
                message = '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n' \
                          'Try running the command with --insecure flag.'

            elif 'Failed to establish a new connection:' in str(error.reason):
                message = 'Failed to establish a new connection: Connection refused.\n' \
                          'Try checking your BASE url configuration.'

            elif error.reason in ('Bad Request', 'Forbidden'):
                error_body = json.loads(error.body)
                message = error_body.get('error')

                if error_body.get('status') == 403:
                    message += '\nTry checking your API key configuration.'
        print_error(str(f'\nUpload {file_type}: {file_name} failed:'))
        print_error(str(message))

    def _remove_temp_file(self, path_to_delete):
        if os.path.exists(path_to_delete) and not os.path.isdir(path_to_delete):
            try:
                os.unlink(path_to_delete)
            except (PermissionError, IsADirectoryError) as error:
                print_error(error)

    def _sort_directories_based_on_dependencies(self, dir_list: List) -> List:
        """Sorts given list of directories based on logic order of content entities that depend on each other

        Args:
            dir_list (List): List of directories to sort

        Returns:
            List. The sorted list of directories.
        """
        srt = {item: index for index, item in enumerate(CONTENT_ENTITY_UPLOAD_ORDER)}
        dir_list.sort(key=lambda item: srt.get(os.path.basename(item)))
        return dir_list

    def _print_summary(self):
        """Prints uploaded files summary
        Successful uploads grid based on `successfully_uploaded_files` attribute in green color
        Failed uploads grid based on `failed_uploaded_files` attribute in red color
        """
        print_color('\n\nUPLOAD SUMMARY:', LOG_COLORS.NATIVE)
        if self.successfully_uploaded_files:
            print_color('\nSUCCESSFUL UPLOADS:', LOG_COLORS.GREEN)
            print_color(tabulate(self.successfully_uploaded_files, headers=['NAME', 'TYPE'],
                                 tablefmt="fancy_grid") + '\n', LOG_COLORS.GREEN)
        if self.failed_uploaded_files:
            print_color('\nFAILED UPLOADS:', LOG_COLORS.RED)
            print_color(tabulate(self.failed_uploaded_files, headers=['NAME', 'TYPE'],
                                 tablefmt="fancy_grid") + '\n', LOG_COLORS.RED)

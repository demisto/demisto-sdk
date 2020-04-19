import demisto_client
import os
import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.tools import print_color, LOG_COLORS, print_v, print_error, get_child_files, \
    get_child_directories, is_path_of_integration_directory, \
    is_path_of_script_directory, is_path_of_playbook_directory, is_path_of_test_playbook_directory, \
    is_path_of_dashboard_directory, is_path_of_widget_directory, is_path_of_incident_field_directory, \
    is_path_of_incident_type_directory, is_path_of_indicator_field_directory, is_path_of_layout_directory, \
    is_path_of_classifier_directory, find_type
from demisto_sdk.commands.unify.unifier import Unifier


class Uploader:
    """Upload a pack specified in self.infile to the remote Demisto instance.
        Attributes:
            path (str): The path of a pack / directory / file to upload.
            verbose (bool): Whether to output a detailed response.
            client (DefaultApi): Demisto-SDK client object.
        """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False):
        self.path = input
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)

    def upload(self):
        """Upload the pack / directory / file to the remote Demisto instance.
        """
        if os.path.isdir(self.path):
            if self.directory_uploader(self.path):
                return 0
            else:
                self.peck_uploader()
        else:
            file_type = find_type(self.path)

            if file_type == "integration":
                self.integration_uploader(self.path)
            elif file_type == "script":
                self.script_uploader(self.path)
            elif file_type == "playbook":
                self.playbook_uploader(self.path)
            elif file_type == "widget":
                self.script_uploader(self.path)
            elif file_type == "incidenttype":
                self.playbook_uploader(self.path)
            elif file_type == "classifier":
                self.script_uploader(self.path)
            elif file_type == "layout":
                self.playbook_uploader(self.path)
            elif file_type == "dashboard":
                self.script_uploader(self.path)
            elif file_type == "incidentfield":
                self.playbook_uploader(self.path)
            else:
                print_error(f'Error: Path input is not valid``. Check the given input path: {self.path}.')
        return 0

    def peck_uploader(self):
        """Extracting the directories of the peck and upload them by directory_uploader
        """
        file_uploaded = False
        list_directories = get_child_directories(self.path)
        for directory in list_directories:
            file_uploaded = self.directory_uploader(directory)
        if not file_uploaded:
            print_error(f'Error: No files to upload``. Check the given input path: {self.path}.')

    def directory_uploader(self, path):
        """Uploads directories by name
        """
        if is_path_of_integration_directory(path):
            list_integrations = get_child_directories(path)
            for integration in list_integrations:
                self.integration_uploader(integration)
            return True

        elif is_path_of_script_directory(path):
            list_script = get_child_directories(path)
            for script in list_script:
                self.script_uploader(script)
            return True

        elif is_path_of_playbook_directory(path) or is_path_of_test_playbook_directory(path):
            list_playbooks = get_child_files(path)
            for playbook in list_playbooks:
                if playbook.endswith('.yml'):
                    self.playbook_uploader(playbook)
            return True

        elif is_path_of_incident_field_directory(path):
            list_incident_fields = get_child_files(path)
            for incident_field in list_incident_fields:
                if incident_field.endswith('.json'):
                    self.incident_field_uploader(incident_field)
            return True

        elif is_path_of_widget_directory(path):
            list_widgets = get_child_files(path)
            for widget in list_widgets:
                if widget.endswith('.json'):
                    self.widget_uploader(widget)
            return True

        elif is_path_of_dashboard_directory(path):
            list_dashboards = get_child_files(path)
            for dashboard in list_dashboards:
                if dashboard.endswith('.json'):
                    self.dashboard_uploader(dashboard)
            return True

        elif is_path_of_layout_directory(path):
            list_layouts = get_child_files(path)
            for layout in list_layouts:
                if layout.endswith('.json'):
                    self.layout_uploader(layout)
            return True

        elif is_path_of_incident_type_directory(path):
            list_incident_types = get_child_files(path)
            for incident_type in list_incident_types:
                if incident_type.endswith('.json'):
                    self.incident_type_uploader(incident_type)
            return True

        elif is_path_of_classifier_directory(path):
            list_classifiers = get_child_files(path)
            for classifiers in list_classifiers:
                if classifiers.endswith('.json'):
                    self.classifiers_uploader(classifiers)
            return True

    def integration_uploader(self, path):
        try:
            if os.path.isdir(path):  # Create a temporary unified yml file
                try:
                    unifier = Unifier(input=path, output=path)
                    path = unifier.merge_script_package_to_yml()[0]
                except IndexError:
                    print_error(f'Error uploading integration from pack. /'
                                f'Check that the given integration path conatinas a valid integraion: {path}.')

                    return 1
                except Exception as err:
                    print_error(str(err))
                    return 1
            # Upload the file to Demisto
            result = self.client.integration_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1

        finally:
            # Remove the temporary file
            if os.path.exists(path):
                try:
                    os.remove(path)
                except (PermissionError, IsADirectoryError):
                    pass

    def script_uploader(self, path):
        """
        try:
            if os.path.isdir(path):  # Create a temporary unified yml file
                try:
                    unifier = Unifier(input=path, output=path)
                    path = unifier.merge_script_package_to_yml()[0]
                except IndexError:
                    print_error(f'Error uploading script from pack. /
                    Check that the given script path conatinas a valid script: {path}.')
                    return 1
                except Exception as err:
                    print_error(str(err))
                    return 1
            # Upload the file to Demisto
            result = self.client.scripts_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1

        finally:
            # Remove the temporary file
            if os.path.exists(path):
                try:
                    os.remove(path)
                except (PermissionError, IsADirectoryError):
                    pass
        """
        print(f'{path} - script_uploader in construction')

    def playbook_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.playbook_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - playbook_uploader in construction')

    def incident_field_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - incident_field_uploader in construction')

    def widget_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - widget_uploader in construction')

    def dashboard_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - dashboard_uploader in construction')

    def layout_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - layout_uploader in construction')

    def indicator_field_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - indicator_field_uploader in construction')

    def incident_type_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - incident_type_uploader in construction')


    def classifiers_uploader(self, path):
        """
        try:
            # Upload the file to Demisto
            result = self.client.incident_field_upload(file=path)

            # Print results
            print_v(f'Result:\n{result.to_str()}', self.log_verbose)
            print_color(f'Uploaded \'{result.name}\' successfully', LOG_COLORS.GREEN)

        except Exception as err:
            print_error(str(err))
            return 1
        """
        print(f'{path} - classifiers_uploader in construction')

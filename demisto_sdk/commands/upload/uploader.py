import demisto_client
import os
import demisto_sdk.commands.common.constants as constants
from demisto_sdk.commands.common.tools import print_color, LOG_COLORS, print_v, print_error, get_child_files, \
    get_child_directories
from demisto_sdk.commands.unify.unifier import Unifier


class Uploader:
    """Upload the files specified in self.infile to the remote Demisto instance.
        Attributes:
            path (str): The path of an file or a package directory to upload.
            verbose (bool): Whether to output a detailed response.
            client (DefaultApi): Demisto-SDK client object.
        """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False):
        self.path = input
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)

    def upload(self):
        """Upload the integration specified in self.infile to the remote Demisto instance.
        """
        if os.path.isdir(self.path):
            list_files_in_dir = get_child_files(self.path)
            if f'{self.path}/pack_metadata.json' in list_files_in_dir:
                self.peck_uploader(self.path)
        else:
            print_color('Error: Path input is not a valid package directory.', LOG_COLORS.RED)
        return 0

    def peck_uploader(self, path):
        list_directories = get_child_directories(path)

        for directory in list_directories:

            if directory.endswith(constants.INTEGRATIONS_DIR):
                list_integrations = get_child_directories(directory)
                for integration in list_integrations:
                    self.integration_uploader(integration)

            if directory.endswith(constants.SCRIPTS_DIR):
                list_script = get_child_directories(directory)
                for script in list_script:
                    self.script_uploader(script)

            if directory.endswith(f'/{constants.PLAYBOOKS_DIR}'):
                list_playbooks = get_child_files(directory)
                for playbook in list_playbooks:
                    if playbook.endswith('.yml'):
                        self.playbook_uploader(playbook)

            if directory.endswith(constants.INCIDENT_FIELDS_DIR):
                list_incident_fields = get_child_files(directory)
                for incident_field in list_incident_fields:
                    if incident_field.endswith('.json'):
                        self.incident_field_uploader(incident_field)

            if directory.endswith(constants.WIDGETS_DIR):
                list_widgets = get_child_files(directory)
                for widget in list_widgets:
                    if widget.endswith('.json'):
                        self.widget_uploader(widget)

            if directory.endswith(constants.DASHBOARDS_DIR):
                list_dashboards = get_child_files(directory)
                for dashboard in list_dashboards:
                    if dashboard.endswith('.json'):
                        self.dashboard_uploader(dashboard)

            if directory.endswith(constants.LAYOUTS_DIR):
                list_layouts = get_child_files(directory)
                for layout in list_layouts:
                    if layout.endswith('.json'):
                        self.layout_uploader(layout)

            if directory.endswith(constants.INDICATOR_FIELDS_DIR):
                list_indicator_fields = get_child_files(directory)
                for indicator_field in list_indicator_fields:
                    if indicator_field.endswith('.json'):
                        self.indicator_field_uploader(indicator_field)

            if directory.endswith(constants.INCIDENT_TYPES_DIR):
                list_incident_types = get_child_files(directory)
                for incident_type in list_incident_types:
                    if incident_type.endswith('.json'):
                        self.incident_type_uploader(incident_type)

            if directory.endswith(constants.INCIDENT_TYPES_DIR):
                list_indicator_types = get_child_files(directory)
                for indicator_type in list_indicator_types:
                    if indicator_type.endswith('.json'):
                        self.indicator_type_uploader(indicator_type)

            if directory.endswith(constants.CLASSIFIERS_DIR):
                list_classifiers = get_child_files(directory)
                for classifiers in list_classifiers:
                    if classifiers.endswith('.json'):
                        self.classifiers_uploader(classifiers)

    def integration_uploader(self, path):
        try:
            if os.path.isdir(path):  # Create a temporary unified yml file
                try:
                    unifier = Unifier(input=path, output=path)
                    path = unifier.merge_script_package_to_yml()[0]
                except IndexError:
                    print_color('Error: Path input is not a valid package directory.', LOG_COLORS.RED)
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
            if self.unify and os.path.exists(path):
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
                    print_color('Error: Path input is not a valid package directory.', LOG_COLORS.RED)
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
            if self.unify and os.path.exists(path):
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

    def indicator_type_uploader(self, path):
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
        print(f'{path} - indicator_type_uploader in construction')

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
import json
import os
import shutil
from distutils.dir_util import copy_tree
from distutils.version import LooseVersion
from typing import Dict, List

import click
import yaml
import yamlordereddictloader
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR, CONNECTIONS_DIR, DASHBOARDS_DIR, DOC_FILES_DIR,
    INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR, INTEGRATION_CATEGORIES, INTEGRATIONS_DIR, LAYOUTS_DIR,
    MARKETPLACE_LIVE_DISCUSSIONS, PACK_INITIAL_VERSION, PACK_SUPPORT_OPTIONS,
    PLAYBOOKS_DIR, REPORTS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR, WIDGETS_DIR,
    XSOAR_AUTHOR, XSOAR_SUPPORT, XSOAR_SUPPORT_URL, GithubContentConfig)
from demisto_sdk.commands.common.tools import (LOG_COLORS,
                                               get_common_server_path,
                                               print_error, print_v,
                                               print_warning)


class Initiator:
    """Initiator creates a new pack/integration/script.

       Attributes:
           output (str): The directory in which init will create the new pack/integration/script
           name (str): The name for the new pack/integration/script directory.
           id (str): The id for the created script/integration.
           integration (bool): Indicates whether to create an integration.
           template (str): If an integration is initialized, specifies the integration template.
           script (bool): Indicates whether to create a script.
           full_output_path (str): The full path to the newly created pack/integration/script
    """

    TEST_DATA_DIR = 'test_data'

    ''' INTEGRATION TEMPLATES CONSTANTS '''
    DEFAULT_INTEGRATION_TEMPLATE = 'BaseIntegration'
    HELLO_WORLD_INTEGRATION = 'HelloWorld'
    HELLO_IAM_WORLD_INTEGRATION = 'HelloIAMWorld'
    HELLO_WORLD_FEED_INTEGRATION = 'FeedHelloWorld'

    INTEGRATION_TEMPLATE_OPTIONS = [HELLO_WORLD_INTEGRATION, HELLO_IAM_WORLD_INTEGRATION, HELLO_WORLD_FEED_INTEGRATION,
                                    DEFAULT_INTEGRATION_TEMPLATE]

    TEMPLATE_INTEGRATION_NAME = '%%TEMPLATE_NAME%%'
    TEMPLATE_INTEGRATION_FILES = {f'{TEMPLATE_INTEGRATION_NAME}.py',
                                  f'{TEMPLATE_INTEGRATION_NAME}.yml',
                                  f'{TEMPLATE_INTEGRATION_NAME}_description.md',
                                  f'{TEMPLATE_INTEGRATION_NAME}_image.png',
                                  f'{TEMPLATE_INTEGRATION_NAME}_test.py',
                                  'Pipfile', 'Pipfile.lock', 'README.md', 'command_examples'}

    DEFAULT_INTEGRATION_TEST_DATA_FILES = {os.path.join(TEST_DATA_DIR, 'baseintegration-dummy.json')}

    HELLO_WORLD_TEST_DATA_FILES = {os.path.join(TEST_DATA_DIR, 'domain_reputation.json'),
                                   os.path.join(TEST_DATA_DIR, 'get_alert.json'),
                                   os.path.join(TEST_DATA_DIR, 'ip_reputation.json'),
                                   os.path.join(TEST_DATA_DIR, 'scan_results.json'),
                                   os.path.join(TEST_DATA_DIR, 'search_alerts.json'),
                                   os.path.join(TEST_DATA_DIR, 'update_alert_status.json'),
                                   os.path.join(TEST_DATA_DIR, 'domain_reputation.json')}

    HELLO_WORLD_FEED_TEST_DATA_FILES = {os.path.join(TEST_DATA_DIR, 'build_iterator_results.json'),
                                        os.path.join(TEST_DATA_DIR, 'get_indicators_command_results.json'),
                                        os.path.join(TEST_DATA_DIR, 'FeedHelloWorld_mock.txt')}

    ''' SCRIPT TEMPLATES CONSTANTS '''
    DEFAULT_SCRIPT_TEMPLATE = 'BaseScript'
    HELLO_WORLD_SCRIPT = 'HelloWorldScript'

    SCRIPT_TEMPLATE_OPTIONS = [HELLO_WORLD_SCRIPT, DEFAULT_SCRIPT_TEMPLATE]

    TEMPLATE_SCRIPT_NAME = '%%TEMPLATE_NAME%%'
    TEMPLATE_SCRIPT_FILES = {f'{TEMPLATE_SCRIPT_NAME}.py',
                             f'{TEMPLATE_SCRIPT_NAME}.yml',
                             f'{TEMPLATE_SCRIPT_NAME}_test.py',
                             'README.md'}

    DEFAULT_SCRIPT_TEST_DATA_FILES = {os.path.join(TEST_DATA_DIR, 'basescript-dummy.json')}

    ''' TEMPLATES PACKS CONSTANTS '''
    DEFAULT_TEMPLATE_PACK_NAME = 'StarterPack'
    HELLO_WORLD_PACK_NAME = 'HelloWorld'
    DEFAULT_TEMPLATES = [DEFAULT_INTEGRATION_TEMPLATE, DEFAULT_SCRIPT_TEMPLATE]
    HELLO_WORLD_BASE_TEMPLATES = [HELLO_WORLD_SCRIPT, HELLO_WORLD_INTEGRATION]

    DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    PACK_INITIAL_VERSION = "1.0.0"
    SUPPORTED_FROM_VERSION = "5.5.0"

    DIR_LIST = [INTEGRATIONS_DIR, SCRIPTS_DIR, INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR,
                PLAYBOOKS_DIR, LAYOUTS_DIR, TEST_PLAYBOOKS_DIR, CLASSIFIERS_DIR, CONNECTIONS_DIR, DASHBOARDS_DIR,
                INDICATOR_TYPES_DIR, REPORTS_DIR, WIDGETS_DIR, DOC_FILES_DIR]

    def __init__(self, output: str, name: str = '', id: str = '', integration: bool = False, template: str = '',
                 category: str = '', script: bool = False, pack: bool = False, demisto_mock: bool = False,
                 common_server: bool = False):
        self.output = output if output else ''
        self.id = id

        self.is_integration = integration
        self.is_script = script
        self.is_pack = pack
        self.demisto_mock = demisto_mock
        self.common_server = common_server
        self.category = category
        self.configuration = Configuration()

        # if no flag given automatically create a pack.
        if not integration and not script and not pack:
            self.is_pack = True

        self.template = self.get_selected_template(template)

        self.full_output_path = ''

        while ' ' in name:
            name = str(input("The directory and file name cannot have spaces in it, Enter a different name: "))

        self.dir_name = name

        self.is_pack_creation = not all([self.is_script, self.is_integration])

    def init(self):
        """Starts the init command process.

        """
        if self.is_integration:
            self.get_created_dir_name(created_object="integration")
            self.get_object_id(created_object="integration")
            return self.integration_init()

        elif self.is_script:
            self.get_created_dir_name(created_object="script")
            self.get_object_id(created_object="script")
            return self.script_init()

        elif self.is_pack:
            self.get_created_dir_name(created_object="pack")
            return self.pack_init()

    def get_selected_template(self, template: str = '') -> str:
        """ Makes sure a valid template is selected

        Args:
            template (str): the given template name (empty string if not given)

        Returns:
            str. A valid template name. If no template was specified, returns the default template name.
        """
        if self.is_integration:
            while template and template not in self.INTEGRATION_TEMPLATE_OPTIONS:
                options_str = ', '.join(self.INTEGRATION_TEMPLATE_OPTIONS)
                template = str(input(f"Enter a valid template name, or press enter to choose the default template"
                                     f" ({self.DEFAULT_INTEGRATION_TEMPLATE}).\nValid options: {options_str}\n"))
            return template if template else self.DEFAULT_INTEGRATION_TEMPLATE

        elif self.is_script:
            while template and template not in self.SCRIPT_TEMPLATE_OPTIONS:
                options_str = ', '.join(self.SCRIPT_TEMPLATE_OPTIONS)
                template = str(input(f"Enter a valid template name, or press enter to choose the default template"
                                     f" ({self.DEFAULT_SCRIPT_TEMPLATE}).\nValid options: {options_str}\n"))
            return template if template else self.DEFAULT_SCRIPT_TEMPLATE

        # if reached here it is a pack init - will be used again if user decides to create an integration
        return template

    def get_created_dir_name(self, created_object: str):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        while not self.dir_name or len(self.dir_name) == 0:
            self.dir_name = str(input(f"Please input the name of the initialized {created_object}: "))
            while ' ' in self.dir_name:
                self.dir_name = str(input("The directory name cannot have spaces in it, Enter a different name: "))

    def get_object_id(self, created_object: str):
        if not self.id:
            if self.is_pack_creation:  # There was no option to enter the ID in this process.
                use_dir_name = str(input(f"Do you want to use the directory name as an "
                                         f"ID for the {created_object}? Y/N "))
            else:
                use_dir_name = str(input(f"No ID given for the {created_object}'s yml file. "
                                         f"Do you want to use the directory name? Y/N "))

            if use_dir_name and use_dir_name.lower() in ['y', 'yes']:
                self.id = self.dir_name
            else:
                while not self.id:
                    self.id = str(input(f"Please enter the id name for the {created_object}: "))

    def pack_init(self) -> bool:
        """Creates a pack directory tree.

        Returns:
            bool. Returns True if pack was created successfully and False otherwise
        """
        # if an output directory given create the pack there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # content-descriptor file indicates we are in "content" repository
        # thus we will create the pack under Packs directory
        elif os.path.isfile('content-descriptor.json'):
            self.full_output_path = os.path.join("Packs", self.dir_name)

        # if in an external repo check for the existence of Packs directory
        # if it does not exist create it
        elif tools.is_external_repository():
            if not os.path.isdir("Packs"):
                print("Creating 'Packs' directory")
                os.mkdir('Packs')
            self.full_output_path = os.path.join("Packs", self.dir_name)

        # if non of the above conditions apply - create the pack in current directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False
        for directory in self.DIR_LIST:
            path = os.path.join(self.full_output_path, directory)
            os.mkdir(path=path)

        self.create_pack_base_files()

        click.echo(
            f"Successfully created the pack {self.dir_name} in: {self.full_output_path}",
            color=LOG_COLORS.GREEN
        )

        metadata_path = os.path.join(self.full_output_path, 'pack_metadata.json')
        with open(metadata_path, 'a') as fp:
            user_response = input("\nWould you like fill pack's metadata file? Y/N ").lower()
            fill_manually = user_response in ['y', 'yes']

            pack_metadata = Initiator.create_metadata(fill_manually)
            self.category = pack_metadata['categories'][0]
            json.dump(pack_metadata, fp, indent=4)

            click.echo(f"Created pack metadata at path : {metadata_path}", color=LOG_COLORS.GREEN)

        create_integration = str(input("\nDo you want to create an integration in the pack? Y/N ")).lower()
        if create_integration in ['y', 'yes']:
            is_same_category = str(input("\nDo you want to set the integration category as you defined in the pack "
                                         "metadata? Y/N ")).lower()

            integration_category = self.category if is_same_category in ['y', 'yes'] else ''
            integration_init = Initiator(output=os.path.join(self.full_output_path, 'Integrations'),
                                         integration=True, common_server=self.common_server,
                                         demisto_mock=self.demisto_mock, template=self.template,
                                         category=integration_category)
            return integration_init.init()

        return True

    def create_pack_base_files(self):
        """
        Create empty 'README.md', '.secrets-ignore', and '.pack-ignore' files that are expected
        to be in the base directory of a pack
        """
        click.echo('Creating pack base files', color=LOG_COLORS.NATIVE)
        fp = open(os.path.join(self.full_output_path, 'README.md'), 'a')
        fp.close()

        fp = open(os.path.join(self.full_output_path, '.secrets-ignore'), 'a')
        fp.close()

        fp = open(os.path.join(self.full_output_path, '.pack-ignore'), 'a')
        fp.close()

    @staticmethod
    def create_metadata(fill_manually: bool, data: Dict = {}) -> Dict:
        """Builds pack metadata JSON content.

        Args:
            fill_manually (bool): Whether to interact with the user to fill in metadata details or not.
            data (dict): Dictionary keys and value to insert into the pack metadata.

        Returns:
            Dict. Pack metadata JSON content.
        """
        pack_metadata = {
            'name': '## FILL MANDATORY FIELD ##',
            'description': '## FILL MANDATORY FIELD ##',
            'support': XSOAR_SUPPORT,
            'currentVersion': PACK_INITIAL_VERSION,
            'author': XSOAR_AUTHOR,
            'url': XSOAR_SUPPORT_URL,
            'email': '',
            'categories': [],
            'tags': [],
            'useCases': [],
            'keywords': []
        }

        if data:
            pack_metadata.update(data)

        if not fill_manually:
            return pack_metadata  # return xsoar template

        pack_metadata['name'] = input("\nDisplay name of the pack: ")
        if not pack_metadata.get('name'):
            pack_metadata['name'] = '## FILL MANDATORY FIELD ##'

        pack_metadata['description'] = input("\nDescription of the pack: ")
        if not pack_metadata.get('description'):
            pack_metadata['description'] = '## FILL MANDATORY FIELD ##'

        pack_metadata['support'] = Initiator.get_valid_user_input(options_list=PACK_SUPPORT_OPTIONS,
                                                                  option_message="\nSupport type of the pack: \n")
        pack_metadata['categories'] = [Initiator.get_valid_user_input(options_list=INTEGRATION_CATEGORIES,
                                                                      option_message="\nPack category options: \n")]

        if pack_metadata.get('support') == XSOAR_SUPPORT:
            pack_metadata['author'] = XSOAR_AUTHOR
            pack_metadata['url'] = XSOAR_SUPPORT_URL

            return pack_metadata

        pack_metadata['author'] = input("\nAuthor of the pack: ")

        if pack_metadata.get('support') != 'community':  # get support details from the user for non community packs
            support_url = input("\nThe url of support, should be a valid support/info URL (optional): ")
            while support_url and "http" not in support_url:
                support_url = input("\nIncorrect input. Please enter full valid url: ")
            pack_metadata['url'] = support_url
            pack_metadata['email'] = input("\nThe email in which users can reach out for support (optional): ")
        else:  # community pack url should refer to the marketplace live discussions
            pack_metadata['url'] = MARKETPLACE_LIVE_DISCUSSIONS

        dev_email = input("\nThe email will be used to inform you for any changes made to your pack (optional): ")
        if dev_email:
            pack_metadata['devEmail'] = [e.strip() for e in dev_email.split(',') if e]

        tags = input("\nTags of the pack, comma separated values: ")
        tags_list = [t.strip() for t in tags.split(',') if t]
        pack_metadata['tags'] = tags_list

        github_users = input("\nPack default reviewers, comma separated github username: ")
        github_users_list = [u.strip() for u in github_users.split(',') if u]
        pack_metadata['githubUser'] = github_users_list

        return pack_metadata

    @staticmethod
    def get_valid_user_input(options_list: List[str], option_message: str) -> str:
        """Gets user input from a list of options, by integer represents the choice.

        Args:
            options_list (List[str]): List of options for the user to choose from.
            option_message (str): The message to show the user along with the list of options.

        Returns:
            str. The chosen option.
        """
        for index, option in enumerate(options_list, start=1):
            option_message += f"[{index}] {option}\n"
        option_message += "\nEnter option: "

        user_input = input(option_message)

        while True:
            try:
                user_choice = int(user_input)
                if user_choice not in range(1, len(options_list) + 1):
                    user_input = input(f"\nInvalid option {user_input}, please enter valid choice: ")
                else:
                    return options_list[user_choice - 1]
            except ValueError:
                user_input = input("\nThe option must be number, please enter valid choice: ")

    def integration_init(self) -> bool:
        """Creates a new integration according to a template.

        Returns:
            bool. True if the integration was created successfully, False otherwise.
        """
        # if output directory given create the integration there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # will create the integration under the Integrations directory of the pack
        elif os.path.isdir(INTEGRATIONS_DIR):
            self.full_output_path = os.path.join(INTEGRATIONS_DIR, self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        integration_template_files = self.get_template_files()
        if not self.get_remote_templates(integration_template_files, dir=INTEGRATIONS_DIR):
            local_template_path = os.path.normpath(os.path.join(__file__, "..", 'templates', self.template))
            copy_tree(str(local_template_path), self.full_output_path)

        if self.id != self.template:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.template)
            self.yml_reformatting(current_suffix=self.template, integration=True)
            self.fix_test_file_import(name_to_change=self.template)

        self.copy_common_server_python()
        self.copy_demistotmock()

        click.echo(f"Finished creating integration: {self.full_output_path}.", color=LOG_COLORS.GREEN)

        return True

    def script_init(self) -> bool:
        """Creates a new script according to a template.

        Returns:
            bool. True if the script was created successfully, False otherwise.
        """
        # if output directory given create the script there
        if self.output:
            self.full_output_path = os.path.join(self.output, self.dir_name)

        # will create the script under the Scripts directory of the pack
        elif os.path.isdir(SCRIPTS_DIR):
            self.full_output_path = os.path.join('Scripts', self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        script_template_files = self.get_template_files()
        if not self.get_remote_templates(script_template_files, dir=SCRIPTS_DIR):
            local_template_path = os.path.normpath(os.path.join(__file__, "..", 'templates', self.template))
            copy_tree(str(local_template_path), self.full_output_path)

        if self.id != self.template:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.template)
            self.yml_reformatting(current_suffix=self.template)
            self.fix_test_file_import(name_to_change=self.template)

        self.copy_common_server_python()
        self.copy_demistotmock()

        click.echo(f"Finished creating script: {self.full_output_path}", color=LOG_COLORS.GREEN)

        return True

    def yml_reformatting(self, current_suffix: str, integration: bool = False):
        """Formats the given yml to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
            integration (bool): Indicates if integration yml is being reformatted.
        """
        with open(os.path.join(self.full_output_path, f"{current_suffix}.yml")) as f:
            yml_dict = yaml.load(f, Loader=yamlordereddictloader.SafeLoader)
        yml_dict["commonfields"]["id"] = self.id
        yml_dict['name'] = self.id

        if LooseVersion(yml_dict.get('fromversion', '0.0.0')) < LooseVersion(self.SUPPORTED_FROM_VERSION):
            yml_dict['fromversion'] = self.SUPPORTED_FROM_VERSION

        if integration:
            yml_dict["display"] = self.id
            yml_dict["category"] = self.category if self.category else Initiator.get_valid_user_input(
                options_list=INTEGRATION_CATEGORIES, option_message="\nIntegration category options: \n")

        with open(os.path.join(self.full_output_path, f"{self.dir_name}.yml"), 'w') as f:
            yaml.dump(
                yml_dict,
                f,
                Dumper=yamlordereddictloader.SafeDumper,
                default_flow_style=False)

        os.remove(os.path.join(self.full_output_path, f"{current_suffix}.yml"))

    def rename(self, current_suffix: str):
        """Renames the python, description, test and image file in the path to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
        """
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}.py"),
                  os.path.join(self.full_output_path, f"{self.dir_name}.py"))
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}_test.py"),
                  os.path.join(self.full_output_path, f"{self.dir_name}_test.py"))
        if self.is_integration:
            os.rename(os.path.join(self.full_output_path, f"{current_suffix}_image.png"),
                      os.path.join(self.full_output_path, f"{self.dir_name}_image.png"))
            os.rename(os.path.join(self.full_output_path, f"{current_suffix}_description.md"),
                      os.path.join(self.full_output_path, f"{self.dir_name}_description.md"))

    def create_new_directory(self, ) -> bool:
        """Creates a new directory for the integration/script/pack.

        Returns:
            bool. True if directory was successfully created, False otherwise.
        """
        try:
            os.mkdir(self.full_output_path)

        except FileExistsError:
            to_delete = str(input(f"The directory {self.full_output_path} "
                                  f"already exists.\nDo you want to overwrite it? Y/N ")).lower()
            while to_delete != 'y' and to_delete != 'n':
                to_delete = str(input("Your response was invalid.\nDo you want to delete it? Y/N ").lower())

            if to_delete in ['y', 'yes']:
                shutil.rmtree(path=self.full_output_path, ignore_errors=True)
                os.mkdir(self.full_output_path)

            else:
                print_error(f"Pack not created in {self.full_output_path}")
                return False

        return True

    def fix_test_file_import(self, name_to_change: str):
        """Fixes the import statement in the _test.py file in the newly created initegration/script

        Args:
            name_to_change (str): The name of the former integration/script to replace in the import.
        """
        with open(os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), 'r') as fp:
            file_contents = fp.read()

        file_contents = file_contents.replace(f'.{name_to_change}', self.dir_name)

        with open(os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), 'w') as fp:
            fp.write(file_contents)

    def copy_common_server_python(self):
        """copy commonserverpython from the base pack"""
        if self.common_server:
            try:
                common_server_path = get_common_server_path(self.configuration.env_dir)
                shutil.copy(common_server_path, self.full_output_path)
            except Exception as err:
                print_v(f'Could not copy CommonServerPython: {str(err)}')

    def copy_demistotmock(self):
        """copy demistomock from content"""
        if self.demisto_mock:
            try:
                shutil.copy(f'{self.configuration.env_dir}/Tests/demistomock/demistomock.py', self.full_output_path)
            except Exception as err:
                print_v(f'Could not copy demistomock: {str(err)}')

    def get_template_files(self):
        """
        Gets the list of the integration/script file names to create according to the selected template.
        Returns:
            set. The names of integration/script files to create.
        """
        if self.is_integration:
            template_files = {filename.replace(self.TEMPLATE_INTEGRATION_NAME, self.template)
                              for filename in self.TEMPLATE_INTEGRATION_FILES}

            if self.template == self.HELLO_WORLD_INTEGRATION:
                template_files = template_files.union(self.HELLO_WORLD_TEST_DATA_FILES)

            elif self.template == self.HELLO_WORLD_FEED_INTEGRATION:
                template_files = template_files.union(self.HELLO_WORLD_FEED_TEST_DATA_FILES)

            elif self.template == self.DEFAULT_INTEGRATION_TEMPLATE:
                template_files = template_files.union(self.DEFAULT_INTEGRATION_TEST_DATA_FILES)
        else:
            template_files = {filename.replace(self.TEMPLATE_SCRIPT_NAME, self.template)
                              for filename in self.TEMPLATE_SCRIPT_FILES}

            if self.template == self.DEFAULT_SCRIPT_TEMPLATE:
                template_files = template_files.union(self.DEFAULT_SCRIPT_TEST_DATA_FILES)
        return template_files

    def get_remote_templates(self, files_list, dir):
        """
        Downloading the object related template-files and saving them in the output path.
        Args:
            files_list: List of files to download.
            dir: The name of the relevant directory (e.g. "Integrations", "Scripts").
        Returns:
            bool. True if the files were downloaded and saved successfully, False otherwise.
        """
        # create test_data dir
        if self.template in [self.HELLO_WORLD_INTEGRATION] + self.DEFAULT_TEMPLATES \
                + [self.HELLO_WORLD_FEED_INTEGRATION]:
            os.mkdir(os.path.join(self.full_output_path, self.TEST_DATA_DIR))

        if self.template in self.DEFAULT_TEMPLATES:
            pack_name = self.DEFAULT_TEMPLATE_PACK_NAME

        elif self.template in self.HELLO_WORLD_BASE_TEMPLATES + [self.HELLO_WORLD_FEED_INTEGRATION]:
            pack_name = self.HELLO_WORLD_PACK_NAME

        else:
            pack_name = self.template

        path = os.path.join('Packs', pack_name, dir, self.template)

        for file in files_list:
            try:
                filename = file
                if 'README.md' in file and self.template not in self.HELLO_WORLD_BASE_TEMPLATES:
                    # This is for the cases when the actual readme file name in content repo
                    # is `README_example.md` - which happens when we do not want the readme
                    # files to appear in https://xsoar.pan.dev/docs/reference/index.
                    filename = file.replace('README.md', 'README_example.md')
                file_content = tools.get_remote_file(
                    os.path.join(path, filename),
                    return_content=True,
                    # Templates available only in the official repo
                    github_repo=GithubContentConfig.OFFICIAL_CONTENT_REPO_NAME
                )
                with open(os.path.join(self.full_output_path, file), 'wb') as f:
                    f.write(file_content)
            except Exception:
                print_warning(f"Could not fetch remote template - {file}. Using local templates instead.")
                return False

        return True

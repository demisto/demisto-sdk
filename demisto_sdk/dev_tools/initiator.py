import os
import shutil
import yaml
import yamlordereddictloader

from typing import Dict
from distutils.dir_util import copy_tree
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS

INTEGRATIONS_DIR = '/Integrations'
SCRIPT_DIR = '/Scripts'
INCIDENT_FIELDS_DIR = '/IncidentFields'
INCIDENT_TYPES_DIR = '/IncidentTypes'
INDICATOR_FIELDS_DIR = '/IndicatorFields'
PLAYBOOKS_DIR = '/Playbooks'
LAYOUTS_DIR = '/Layouts'
TEST_PLAYBOOKS_DIR = '/TestPlaybooks'
CLASSIFIERS_DIR = '/Classifiers'
CONNECTIONS_DIR = '/Connections'
DASHBOARDS_DIR = '/Dashboards'
MISC_DIR = '/Misc'
REPORTS_DIR = '/Reports'
WIDGETS_DIR = '/Widgets'

HELLO_WORLD_INTEGRATION = 'HelloWorld'
HELLO_WORLD_SCRIPT = 'HelloWorldScript'


class Initiator:
    """Initiator creates a new pack/integration/script.

    Attributes:
        output_dir (str): The directory in which init will create the new pack/integration/script
        name (str): The name for the new pack/integration/script
        integration (bool): Indicates whether to create an integration.
        script (bool): Indicates whether to create a script.
        full_path (str): The full path to the newly created pack/integration/script
    """

    def __init__(self, output_dir: str, name: str, integration: bool = False, script: bool = False):
        if output_dir:
            self.output_dir = output_dir

        else:
            self.output_dir = ''

        self.name = name
        self.integration = integration
        self.script = script
        self.full_path = ''

    def init(self):
        """Starts the init command process.

        """
        if self.integration:
            self.check_name(created_object="integration")
            self.integration_init()

        elif self.script:
            self.check_name(created_object="script")
            self.script_init()

        else:
            self.check_name(created_object="pack")
            self.pack_init()

    def check_name(self, created_object: str):
        """Makes sure a name is given for the created object

        Args:
            created_object (str): the type of the created object (integration/script/pack)
        """
        while self.name is None:
            print(f"Please input the name of the initialized {created_object}:")
            self.name = str(input())

    def pack_init(self) -> bool:
        """Creates a pack directory tree.

        Returns:
            bool. Returns True if pack was created successfully and False otherwise
        """
        # if an output directory given create the pack there
        if len(self.output_dir) > 0:
            self.full_path = self.output_dir + '/' + self.name

        # content-descriptor file indicates we are in "content" repository
        # thus we will create the pack under Packs directory
        elif os.path.isfile('content-descriptor.json'):
            self.full_path = "Packs/" + self.name

        # if non of the above conditions apply - create the pack in current directory
        else:
            self.full_path = self.name

        if not self.create_new_directory():
            return False

        os.mkdir(self.full_path + INCIDENT_FIELDS_DIR)
        os.mkdir(self.full_path + INDICATOR_FIELDS_DIR)
        os.mkdir(self.full_path + CLASSIFIERS_DIR)
        os.mkdir(self.full_path + CONNECTIONS_DIR)
        os.mkdir(self.full_path + DASHBOARDS_DIR)
        os.mkdir(self.full_path + INCIDENT_TYPES_DIR)
        os.mkdir(self.full_path + MISC_DIR)
        os.mkdir(self.full_path + REPORTS_DIR)
        os.mkdir(self.full_path + WIDGETS_DIR)
        os.mkdir(self.full_path + INTEGRATIONS_DIR)
        os.mkdir(self.full_path + LAYOUTS_DIR)
        os.mkdir(self.full_path + PLAYBOOKS_DIR)
        os.mkdir(self.full_path + SCRIPT_DIR)
        os.mkdir(self.full_path + TEST_PLAYBOOKS_DIR)

        with open(self.full_path + '/CHANGELOG.md', 'a') as fp:
            fp.write("## [Unreleased]")

        fp = open(self.full_path + '/README.md', 'a')
        fp.close()

        with open(self.full_path + '/pack-metadata.json', 'a') as fp:
            fp.write('[]')

        fp = open(self.full_path + '/.secrets-ignore', 'a')
        fp.close()

        fp = open(self.full_path + '/.pack-ignore', 'a')
        fp.close()

        print_color(f"Successfully created the pack {self.name} in: {self.full_path}", LOG_COLORS.GREEN)

        print("\nDo you want to create an integration in the pack? Y/N")
        create_integration = str(input()).lower()
        if create_integration == 'y':
            self.check_name(created_object="integration")
            self.output_dir = self.full_path + INTEGRATIONS_DIR
            return self.integration_init()

        return True

    def integration_init(self) -> bool:
        """Creates a new integration according to a template.

        Returns:
            bool. True if the integration was created successfully, False otherwise.
        """
        # if output directory given create the integration there
        if len(self.output_dir) > 0:
            self.full_path = self.output_dir + '/' + self.name

        # the file pack-metadata indicates we are in a pack directory
        # thus we will create the integration under the Integrations directory of the pack
        elif os.path.isfile("pack-metadata.json"):
            self.full_path = 'Integrations/' + self.name

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_path = self.name

        if not self.create_new_directory():
            return False

        hello_world_path = os.path.normpath(os.path.join(__file__, "..", "..", 'common', 'schemas',
                                                         HELLO_WORLD_INTEGRATION))

        copy_tree(str(hello_world_path), self.full_path)
        if self.name != HELLO_WORLD_INTEGRATION:
            self.rename(current_suffix=HELLO_WORLD_INTEGRATION)
            self.yml_reformatting(current_suffix=HELLO_WORLD_INTEGRATION)

        print_color(f"Finished creating integration: {self.full_path}.", LOG_COLORS.GREEN)

        return True

    def script_init(self) -> bool:
        """Creates a new script according to a template.

        Returns:
            bool. True if the script was created successfully, False otherwise.
        """
        # if output directory given create the script there
        if len(self.output_dir) > 0:
            full_path = self.output_dir + '/' + self.name

        # the file pack-metadata indicates we are in a pack directory
        # thus we will create the script under the Scripts directory of the pack
        elif os.path.isfile("pack-metadata.json"):
            full_path = 'Scripts/' + self.name

        # if non of the conditions above apply - create the integration in the local directory
        else:
            full_path = self.name

        if not self.create_new_directory():
            return False

        hello_world_path = os.path.normpath(os.path.join(__file__, "..", "..", 'common', 'schemas',
                                                         HELLO_WORLD_SCRIPT))

        copy_tree(str(hello_world_path), full_path)
        if self.name != HELLO_WORLD_SCRIPT:
            self.rename(current_suffix=HELLO_WORLD_SCRIPT)
            self.yml_reformatting(current_suffix=HELLO_WORLD_SCRIPT)

        print_color(f"Finished creating script: {full_path}", LOG_COLORS.GREEN)

        return True

    def yml_reformatting(self, current_suffix: str):
        """Formats the given yml to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
        """
        yml_dict = self.get_yml_data_as_dict(file_path=f"{self.full_path}/{current_suffix}.yml")
        yml_dict["commonfields"]["id"] = self.name
        yml_dict['name'] = self.name
        yml_dict["display"] = self.name

        with open(f"{self.full_path}/{self.name}.yml", 'w') as f:
            yaml.dump(
                yml_dict,
                f,
                Dumper=yamlordereddictloader.SafeDumper,
                default_flow_style=False)

        os.remove(f"{self.full_path}/{current_suffix}.yml")

    def rename(self, current_suffix: str):
        """Renames the python, description, test and image file in the path to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
        """
        os.rename(f"{self.full_path}/{current_suffix}.py", f"{self.full_path}/{self.name}.py")
        os.rename(f"{self.full_path}/{current_suffix}_description.md", f"{self.full_path}/{self.name}_description.md")
        os.rename(f"{self.full_path}/{current_suffix}_test.py", f"{self.full_path}/{self.name}_test.py")
        if self.integration:
            os.rename(f"{self.full_path}/{current_suffix}_image.png", f"{self.full_path}/{self.name}_image.png")

    def create_new_directory(self,) -> bool:
        """Creates a new directory for the integration/script/pack.

        Returns:
            bool. True if directory was successfully created, False otherwise.
        """
        try:
            os.mkdir(self.full_path)

        except FileExistsError:
            print_error(f"The directory {self.full_path} already exists.\nDo you want to overwrite it? Y/N")
            to_delete = str(input()).lower()
            while to_delete != 'y' and to_delete != 'n':
                print_error(f"Your response was invalid.\nDo you want to delete it? Y/N")
                to_delete = str(input()).lower()

            if to_delete == 'y':
                shutil.rmtree(path=self.full_path, ignore_errors=True)
                os.mkdir(self.full_path)

            else:
                print_error(f"Pack not created in {self.full_path}")
                return False

        return True

    def get_yml_data_as_dict(self, file_path: str) -> Dict:
        """Converts YML file data to Dict.

        Args:
            file_path (str): The path to the .yml file

        Returns:
            Dict. Data from YML.
        """
        with open(file_path) as f:
            return yaml.load(f, Loader=yamlordereddictloader.SafeLoader)

    @staticmethod
    def add_sub_parser(subparsers):
        parser = subparsers.add_parser('init',
                                       help='Initiate a new Pack, Integration or Script.')
        parser.add_argument("-n", "--name", help="The name of the object you want to create")
        parser.add_argument("-o", "--outdir", help="The output dir to write the object into")
        parser.add_argument("--integration", help="Create an Integration", action='store_true')
        parser.add_argument("--script", help="Create a script", action='store_true')

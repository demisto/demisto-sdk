import os
import shutil
import yaml
import yamlordereddictloader

from typing import Dict
from distutils.dir_util import copy_tree
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS
from demisto_sdk.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR, INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, \
    INDICATOR_FIELDS_DIR, PLAYBOOKS_DIR, LAYOUTS_DIR, TEST_PLAYBOOKS_DIR, CLASSIFIERS_DIR, CONNECTIONS_DIR, \
    DASHBOARDS_DIR, MISC_DIR, REPORTS_DIR, WIDGETS_DIR


class Initiator:
    """Initiator creates a new pack/integration/script.

       Attributes:
           output_dir (str): The directory in which init will create the new pack/integration/script
           name (str): The name for the new pack/integration/script directory.
           id (str): The id for the created script/integration.
           integration (bool): Indicates whether to create an integration.
           script (bool): Indicates whether to create a script.
           full_output_path (str): The full path to the newly created pack/integration/script
    """

    def __init__(self, output_dir: str, name: str = '', id: str = '', integration: bool = False, script: bool = False,
                 pack: bool = False):
        self.output_dir = output_dir if output_dir else ''
        self.id = id

        self.is_integration = integration
        self.is_script = script
        self.is_pack = pack

        # if no flag given automatically create a pack.
        if not integration and not script and not pack:
            self.is_pack = True

        self.full_output_path = ''

        if name is not None and len(name) != 0:
            while ' ' in name:
                name = str(input("The directory and file name cannot have spaces in it, Enter a different name: "))

        self.dir_name = name
        self.is_pack_creation = not all([self.is_script, self.is_integration])

    HELLO_WORLD_INTEGRATION = 'HelloWorld'
    HELLO_WORLD_SCRIPT = 'HelloWorldScript'
    DIR_LIST = [INTEGRATIONS_DIR, SCRIPTS_DIR, INCIDENT_FIELDS_DIR, INCIDENT_TYPES_DIR, INDICATOR_FIELDS_DIR,
                PLAYBOOKS_DIR, LAYOUTS_DIR, TEST_PLAYBOOKS_DIR, CLASSIFIERS_DIR, CONNECTIONS_DIR, DASHBOARDS_DIR,
                MISC_DIR, REPORTS_DIR, WIDGETS_DIR]

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
                                         f"ID for the {created_object}? Y/N"))
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
        if len(self.output_dir) > 0:
            self.full_output_path = os.path.join(self.output_dir, self.dir_name)

        # content-descriptor file indicates we are in "content" repository
        # thus we will create the pack under Packs directory
        elif os.path.isfile('content-descriptor.json'):
            self.full_output_path = os.path.join("Packs", self.dir_name)

        # if non of the above conditions apply - create the pack in current directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False
        for directory in self.DIR_LIST:
            path = os.path.join(self.full_output_path, directory)
            os.mkdir(path=path)

        with open(os.path.join(self.full_output_path, 'CHANGELOG.md'), 'a') as fp:
            fp.write("## [Unreleased]")

        fp = open(os.path.join(self.full_output_path, 'README.md'), 'a')
        fp.close()

        with open(os.path.join(self.full_output_path, 'metadata.json'), 'a') as fp:
            # TODO fill this once metadata.json script is ready
            fp.write('[]')

        fp = open(os.path.join(self.full_output_path, '.secrets-ignore'), 'a')
        fp.close()

        fp = open(os.path.join(self.full_output_path, '.pack-ignore'), 'a')
        fp.close()

        print_color(f"Successfully created the pack {self.dir_name} in: {self.full_output_path}", LOG_COLORS.GREEN)

        create_integration = str(input("\nDo you want to create an integration in the pack? Y/N ")).lower()
        if create_integration in ['y', 'yes']:
            integration_init = Initiator(output_dir=os.path.join(self.full_output_path, 'Integrations'),
                                         integration=True)
            return integration_init.init()

        return True

    def integration_init(self) -> bool:
        """Creates a new integration according to a template.

        Returns:
            bool. True if the integration was created successfully, False otherwise.
        """
        # if output directory given create the integration there
        if len(self.output_dir) > 0:
            self.full_output_path = os.path.join(self.output_dir, self.dir_name)

        # will create the integration under the Integrations directory of the pack
        elif os.path.isdir(INTEGRATIONS_DIR):
            self.full_output_path = os.path.join('Integrations', self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        hello_world_path = os.path.normpath(os.path.join(__file__, "..", "..", 'common', 'templates',
                                                         self.HELLO_WORLD_INTEGRATION))

        copy_tree(str(hello_world_path), self.full_output_path)
        if self.id != self.HELLO_WORLD_INTEGRATION:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.HELLO_WORLD_INTEGRATION)
            self.yml_reformatting(current_suffix=self.HELLO_WORLD_INTEGRATION)
            self.fix_test_file_import(name_to_change=self.HELLO_WORLD_INTEGRATION)

        print_color(f"Finished creating integration: {self.full_output_path}.", LOG_COLORS.GREEN)

        return True

    def script_init(self) -> bool:
        """Creates a new script according to a template.

        Returns:
            bool. True if the script was created successfully, False otherwise.
        """
        # if output directory given create the script there
        if len(self.output_dir) > 0:
            self.full_output_path = os.path.join(self.output_dir, self.dir_name)

        # will create the script under the Scripts directory of the pack
        elif os.path.isdir(SCRIPTS_DIR):
            self.full_output_path = os.path.join('Scripts', self.dir_name)

        # if non of the conditions above apply - create the integration in the local directory
        else:
            self.full_output_path = self.dir_name

        if not self.create_new_directory():
            return False

        hello_world_path = os.path.normpath(os.path.join(__file__, "..", "..", 'common', 'templates',
                                                         self.HELLO_WORLD_SCRIPT))

        copy_tree(str(hello_world_path), self.full_output_path)
        if self.id != self.HELLO_WORLD_SCRIPT:
            # note rename does not work on the yml file - that is done in the yml_reformatting function.
            self.rename(current_suffix=self.HELLO_WORLD_SCRIPT)
            self.yml_reformatting(current_suffix=self.HELLO_WORLD_SCRIPT)
            self.fix_test_file_import(name_to_change=self.HELLO_WORLD_SCRIPT)

        print_color(f"Finished creating script: {self.full_output_path}", LOG_COLORS.GREEN)

        return True

    def yml_reformatting(self, current_suffix: str):
        """Formats the given yml to fit the newly created integration/script

        Args:
            current_suffix (str): The yml file name (HelloWorld or HelloWorldScript)
        """
        yml_dict = self.get_yml_data_as_dict(file_path=os.path.join(self.full_output_path, f"{current_suffix}.yml"))
        yml_dict["commonfields"]["id"] = self.id
        yml_dict['name'] = self.id
        yml_dict["display"] = self.id

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
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}_description.md"),
                  os.path.join(self.full_output_path, f"{self.dir_name}_description.md"))
        os.rename(os.path.join(self.full_output_path, f"{current_suffix}_test.py"),
                  os.path.join(self.full_output_path, f"{self.dir_name}_test.py"))
        if self.is_integration:
            os.rename(os.path.join(self.full_output_path, f"{current_suffix}_image.png"),
                      os.path.join(self.full_output_path, f"{self.dir_name}_image.png"))

    def create_new_directory(self,) -> bool:
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
                to_delete = str(input(f"Your response was invalid.\nDo you want to delete it? Y/N ").lower())

            if to_delete in ['y', 'yes']:
                shutil.rmtree(path=self.full_output_path, ignore_errors=True)
                os.mkdir(self.full_output_path)

            else:
                print_error(f"Pack not created in {self.full_output_path}")
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

    def fix_test_file_import(self, name_to_change: str):
        """Fixes the import statement in the _test.py file in the newly created initegration/script

        Args:
            name_to_change (str): The name of the former integration/script to replace in the import.
        """
        with open(os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), 'r') as fp:
            file_contents = fp.read()
            file_contents = file_contents.replace(name_to_change, self.dir_name)

        with open(os.path.join(self.full_output_path, f"{self.dir_name}_test.py"), 'w') as fp:
            fp.write(file_contents)

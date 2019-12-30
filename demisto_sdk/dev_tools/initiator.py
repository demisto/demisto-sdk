import os
import shutil
from demisto_sdk.common.tools import print_error, print_color, LOG_COLORS

INTEGRATIONS_DIR = '/Integrations'
SCRIPT_DIR = '/Scripts'
INCIDENT_FIELDS_DIR = '/IncidentFields'
INDICATOR_TYPES_DIR = '/IndicatorTypes'
PLAYBOOKS_DIR = '/Playbooks'
LAYOUTS_DIR = '/Layouts'
TEST_PLAYBOOKS_DIR = '/TestPlaybooks'


class Initiator:
    def __init__(self, output_dir: str, name: str, integration: bool = False, script: bool = False):

        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = ''

        self.name = name
        self.integration = integration
        self.script = script

    def init(self):
        self.check_name()
        if self.integration:
            self.integration_init()

        if self.script:
            self.script_init()

        else:
            self.pack_init()

    def check_name(self):
        if self.name is None:
            print("Please input the name of the initialized object:\n")
            self.name = str(input())

    def pack_init(self):
        full_path = self.output_dir + '/' + self.name
        try:
            os.mkdir(full_path)

        except FileExistsError:
            to_delete = ''
            print_error(f"The directory {full_path} already exists.\nDo you want to delete it?\n")

            while to_delete != 'y' and to_delete != 'n':
                print_error(f"Your response was invalid.\nDo you want to delete it? Y/N")
                to_delete = str(input()).lower()

            if to_delete == 'y':
                shutil.rmtree(path=full_path, ignore_errors=True)
                os.mkdir(full_path)

            else:
                print_error(f"Pack not created in {full_path}")
                return False

        os.mkdir(full_path + INCIDENT_FIELDS_DIR)
        os.mkdir(full_path + INDICATOR_TYPES_DIR)
        os.mkdir(full_path + INTEGRATIONS_DIR)
        os.mkdir(full_path + LAYOUTS_DIR)
        os.mkdir(full_path + PLAYBOOKS_DIR)
        os.mkdir(full_path + SCRIPT_DIR)
        os.mkdir(full_path + TEST_PLAYBOOKS_DIR)

        with open(full_path + '/CHANGELOG.md', 'a') as fp:
            fp.write("## [Unreleased]")

        fp = open(full_path + '/README.md', 'a')
        fp.close()

        with open(full_path + '/pack-metadata.json', 'a') as fp:
            fp.write('[]')

        fp = open(full_path + '/.secrets-ignore', 'a')
        fp.close()

        fp = open(full_path + '/.pack-ignore', 'a')
        fp.close()

        print_color(f"Successfully created the pack {self.name} in {full_path}", LOG_COLORS.GREEN)
        return True

    def integration_init(self):
        return True

    def script_init(self):
        return True

    @staticmethod
    def add_sub_parser(subparsers):
        parser = subparsers.add_parser('init',
                                       help='Initiate a new Pack, Integration or Script.')
        parser.add_argument("-n", "--name", help="The name of the object you want to create")
        parser.add_argument("-o", "--outdir", help="The output dir to write the object into")
        parser.add_argument("--integration", help="Create an Integration", action='store_true')
        parser.add_argument("--script", help="Create a script", action='store_true')

import os
import glob
import shutil
import zipfile
import io
import yaml
from ..common.constants import INTEGRATIONS_DIR, MISC_DIR, PLAYBOOKS_DIR, REPORTS_DIR, DASHBOARDS_DIR, \
    WIDGETS_DIR, SCRIPTS_DIR, INCIDENT_FIELDS_DIR, CLASSIFIERS_DIR, LAYOUTS_DIR, CONNECTIONS_DIR, \
    BETA_INTEGRATIONS_DIR, INDICATOR_FIELDS_DIR, INCIDENT_TYPES_DIR, TEST_PLAYBOOKS_DIR, PACKS_DIR, DIR_TO_PREFIX
from ..common.tools import get_child_directories, get_child_files, print_color, LOG_COLORS
from ..common.sdk_baseclass import SDKClass
from .unifier import Unifier


class ContentCreator(SDKClass):

    def __init__(self, artifacts_path: str, content_bundle_path='',
                 test_bundle_path='', packs_bundle_path='', preserve_bundles=False):
        self.artifacts_path = artifacts_path if artifacts_path else '/home/circleci/project/artifacts'
        self.preserve_bundles = preserve_bundles

        # temp folder names
        self.content_bundle = content_bundle_path if content_bundle_path else os.path.join(self.artifacts_path,
                                                                                           'bundle_content')
        self.test_bundle = test_bundle_path if test_bundle_path else os.path.join(self.artifacts_path,
                                                                                  'bundle_test')
        self.packs_bundle = packs_bundle_path if packs_bundle_path else os.path.join(self.artifacts_path,
                                                                                     'bundle_packs')

        # directories in which content resides
        self.content_directories = [
            BETA_INTEGRATIONS_DIR,
            CLASSIFIERS_DIR,
            CONNECTIONS_DIR,
            DASHBOARDS_DIR,
            INCIDENT_FIELDS_DIR,
            INCIDENT_TYPES_DIR,
            INDICATOR_FIELDS_DIR,
            INTEGRATIONS_DIR,
            LAYOUTS_DIR,
            MISC_DIR,
            PLAYBOOKS_DIR,
            REPORTS_DIR,
            SCRIPTS_DIR,
            WIDGETS_DIR,
        ]

        self.packages_to_skip = ['HelloWorld', 'HelloWorldSimple', 'HelloWorldScript']

        # zip files names (the extension will be added later - shutil demands file name without extension)
        self.content_zip = 'content_new'
        self.test_zip = 'content_test'
        self.packs_zip = 'content_packs'

        # server can't handle long file names
        self.file_name_max_size = 85
        self.long_file_names = []

    def create_unifieds_and_copy(self, package_dir, dest_dir='', skip_dest_dir=''):
        '''
        For directories that have packages, aka subdirectories for each integration/script
        e.g. "Integrations", "Beta_Integrations", "Scripts". Creates a unified yml and writes
        it to the dest_dir

        Arguments:
            package_dir: (str)
                Path to directory in which there are package subdirectories. e.g. "Integrations",
                "Beta_Integrations", "Scripts"
            dest_dir: (str)
                Path to destination directory to which the unified yml for a package should be written
            skip_dest_dir: (str)
                Path to the directory to which the unified yml for a package should be written in the
                case the package is part of the skipped list
        '''
        dest_dir = dest_dir if dest_dir else self.content_bundle
        skip_dest_dir = skip_dest_dir if skip_dest_dir else self.test_bundle

        scanned_packages = glob.glob(os.path.join(package_dir, '*/'))
        package_dir_name = os.path.basename(package_dir)
        for package in scanned_packages:
            ymls = glob.glob(os.path.join(package, '*.yml'))
            should_unify = True
            if not ymls or ymls[0].endswith('_unified.yml'):
                should_unify = False
            if should_unify:
                unification_tool = Unifier(package, package_dir_name, dest_dir)
                if any(package_to_skip in package for package_to_skip in self.packages_to_skip):
                    # there are some packages that we don't want to include in the content zip
                    # for example HelloWorld integration
                    unification_tool = Unifier(package, package_dir_name, skip_dest_dir)
                    print('skipping {}'.format(package))
                unification_tool.merge_script_package_to_yml()
            else:
                print_color('Skipping package: {} - No yml files found in the package directory'.format(package),
                            LOG_COLORS.YELLOW)

    def add_tools_to_bundle(self, bundle):
        for directory in glob.glob(os.path.join('Tools', '*')):
            zipf = zipfile.ZipFile(os.path.join(bundle, f'tools-{os.path.basename(directory)}.zip'), 'w',
                                   zipfile.ZIP_DEFLATED)
            zipf.comment = b'{ "system": true }'
            for root, _, files in os.walk(directory):
                for file_name in files:
                    zipf.write(os.path.join(root, file_name), file_name)
            zipf.close()

    # def copy_playbook_yml(self, path, out_path, *args):
    #     '''Add "playbook-" prefix to playbook file's copy destination filename if it wasn't already present'''
    #     dest_dir_path = os.path.dirname(out_path)
    #     dest_file_name = os.path.basename(out_path)
    #     if not dest_file_name.startswith('playbook-'):
    #         new_name = '{}{}'.format('playbook-', dest_file_name)
    #         out_path = os.path.join(dest_dir_path, new_name)
    #     shutil.copyfile(path, out_path)

    def copy_content_yml(self, path, out_path, yml_info):
        parent_dir_name = os.path.basename(os.path.dirname(path))
        if parent_dir_name in DIR_TO_PREFIX and not os.path.basename(path).startswith('playbook-'):
            script_obj = yml_info
            if parent_dir_name != 'Scripts':
                script_obj = yml_info['script']
            with io.open(path, mode='r', encoding='utf-8') as file_:
                yml_text = file_.read()
            unifier = Unifier(path, parent_dir_name, out_path)
            out_map = unifier.write_yaml_with_docker(yml_text, yml_info, script_obj)
            if len(out_map.keys()) > 1:
                print(" - yaml generated multiple files: {}".format(out_map.keys()))
            return
        # not a script or integration file. Simply copy
        shutil.copyfile(path, out_path)

    def copy_dir_yml(self, dir_path, bundle):
        scan_files = glob.glob(os.path.join(dir_path, '*.yml'))
        content_files = 0
        # dir_name = os.path.basename(dir_path)
        # copy_func = copy_playbook_yml if dir_name in ['Playbooks', 'TestPlaybooks'] else copy_content_yml
        for path in scan_files:
            if len(os.path.basename(path)) >= self.file_name_max_size:
                self.long_file_names.append(path)

            with open(path, 'r') as file_:
                yml_info = yaml.safe_load(file_)

            ver = yml_info.get('fromversion', '0')
            print(f' - processing: {ver} ({path})')
            self.copy_content_yml(path, os.path.join(bundle, os.path.basename(path)), yml_info)
            content_files += 1
        print(f' - total files: {content_files}')

    def copy_dir_json(self, dir_path, bundle):
        # handle *.json files
        dir_name = os.path.basename(dir_path)
        scan_files = glob.glob(os.path.join(dir_path, '*.json'))
        for path in scan_files:
            dpath = os.path.basename(path)
            # this part is a workaround because server doesn't support indicatorfield-*.json naming
            if dir_name == 'IndicatorFields':
                new_path = dpath.replace('incidentfield-', 'incidentfield-indicatorfield-')
                if os.path.isfile(new_path):
                    raise NameError('Failed while trying to create {}. File already exists.'.format(new_path))
                dpath = new_path

            if len(dpath) >= self.file_name_max_size:
                self.long_file_names.append(os.path.basename(dpath))

            shutil.copyfile(path, os.path.join(bundle, dpath))

    def copy_dir_files(self, *args):
        # handle *.json files
        self.copy_dir_json(*args)
        # handle *.yml files
        self.copy_dir_yml(*args)

    def copy_test_files(self, test_playbooks_dir=TEST_PLAYBOOKS_DIR):
        print('Copying test files to test bundle')
        scan_files = glob.glob(os.path.join(test_playbooks_dir, '*'))
        for path in scan_files:
            if os.path.isdir(path):
                non_circle_tests = glob.glob(os.path.join(path, '*'))
                for new_path in non_circle_tests:
                    print(f'copying path {new_path}')
                    shutil.copyfile(new_path, os.path.join(self.test_bundle, os.path.basename(new_path)))

            else:
                print(f'Copying path {path}')
                shutil.copyfile(path, os.path.join(self.test_bundle, os.path.basename(path)))

    def copy_packs_content_to_old_bundles(self, packs):
        for pack in packs:
            # each pack directory has it's own content subdirs, 'Integrations',
            # 'Scripts', 'TestPlaybooks', 'Layouts' etc.
            sub_dirs_paths = get_child_directories(pack)
            for sub_dir_path in sub_dirs_paths:
                dir_name = os.path.basename(sub_dir_path)
                if dir_name == 'TestPlaybooks':
                    self.copy_test_files(self.test_bundle, sub_dir_path)
                else:
                    # handle one-level deep content
                    self.copy_dir_files(sub_dir_path, self.content_bundle)
                    if dir_name in DIR_TO_PREFIX:
                        # then it's a directory with nested packages that need to be handled
                        # handle nested packages
                        self.create_unifieds_and_copy(sub_dir_path)

    def copy_packs_content_to_packs_bundle(self, packs):
        for pack in packs:
            pack_name = os.path.basename(pack)
            pack_dst = os.path.join(self.packs_bundle, pack_name)
            os.mkdir(pack_dst)
            pack_dirs = get_child_directories(pack)
            pack_files = get_child_files(pack)
            # copy first level pack files over
            for file_path in pack_files:
                shutil.copy(file_path, os.path.join(pack_dst, os.path.basename(file_path)))
            # handle content directories in the pack
            for content_dir in pack_dirs:
                dir_name = os.path.basename(content_dir)
                dest_dir = os.path.join(pack_dst, dir_name)
                os.mkdir(dest_dir)
                if dir_name in DIR_TO_PREFIX:
                    packages_dirs = get_child_directories(content_dir)
                    for package_dir in packages_dirs:
                        package_dir_name = os.path.basename(package_dir)
                        unifier = Unifier(package_dir, dir_name, dest_dir)
                        unifier.merge_script_package_to_yml()

                        # also copy CHANGELOG markdown files over (should only be one per package)
                        package_files = get_child_files(package_dir)
                        changelog_files = [
                            file_path
                            for file_path in package_files if 'CHANGELOG.md' in file_path
                        ]
                        for md_file_path in changelog_files:
                            md_out_name = '{}-{}_CHANGELOG.md'.format(DIR_TO_PREFIX.get(dir_name), package_dir_name)
                            shutil.copyfile(md_file_path, os.path.join(dest_dir, md_out_name))
                else:
                    self.copy_dir_files(content_dir, dest_dir)

    def create_content(self):
        print('Starting to create content artifact...')

        try:
            print('creating dir for bundles...')
            for bundle_dir in [self.content_bundle, self.test_bundle, self.packs_bundle]:
                os.mkdir(bundle_dir)
            
            self.add_tools_to_bundle(self.content_bundle)

            for package_dir in DIR_TO_PREFIX:
                # handles nested package directories
                self.create_unifieds_and_copy(package_dir)
            
            for content_dir in self.content_directories:
                print(f'Copying dir {content_dir} to bundles...')
                self.copy_dir_files(content_dir, self.content_bundle)
            
            self.copy_test_files()

            # handle copying packs content to bundles for zipping to content_new.zip and content_test.zip
            packs = get_child_directories(PACKS_DIR)
            self.copy_packs_content_to_old_bundles(packs)

            # handle copying packs content to packs_bundle for zipping to `content_packs.zip`
            self.copy_packs_content_to_packs_bundle(packs)

            print('Copying content descriptor to content and test bundles')
            for bundle_dir in [self.content_bundle, self.test_bundle]:
                shutil.copyfile('content-descriptor.json', os.path.join(bundle_dir, 'content-descriptor.json'))
            
            print('copying common server doc to content bundle')
            shutil.copyfile('./Documentation/doc-CommonServer.json', 
                            os.path.join(self.content_bundle, 'doc-CommonServer.json'))

            print('Compressing bundles...')
            shutil.make_archive(self.content_zip, 'zip', self.content_bundle)
            shutil.make_archive(self.test_zip, 'zip', self.test_zip)
            shutil.make_archive(self.packs_zip, 'zip', self.packs_bundle)
            shutil.copyfile(self.content_zip + '.zip', os.path.join(self.artifacts_path, self.content_zip + '.zip'))
            shutil.copyfile(self.test_zip + '.zip', os.path.join(self.artifacts_path, self.test_zip + '.zip'))
            shutil.copyfile(self.packs_zip + '.zip', os.path.join(self.artifacts_path, self.packs_zip + '.zip'))
            shutil.copyfile("./Tests/id_set.json", os.path.join(self.artifacts_path, "id_set.json"))
            shutil.copyfile('release-notes.md', os.path.join(self.artifacts_path, 'release-notes.md'))
            print(f'finished create content artifacts at {self.artifacts_path}')
        finally:
            if not self.preserve_bundles:
                if os.path.exists(self.content_bundle):
                    shutil.rmtree(self.content_bundle)
                if os.path.exists(self.test_bundle):
                    shutil.rmtree(self.test_bundle)
                if os.path.exists(self.packs_bundle):
                    shutil.rmtree(self.packs_bundle)

    @staticmethod
    def add_sub_parser(subparsers):
        parser = subparsers.add_parser('create',
                                       help='Create content artifacts')
        parser.add_argument('-a', '--artifacts_path', 
                            help='The path of the directory in which you want to save the created content artifacts')
        parser.add_argument('-p', '--preserve_bundles', action='store_true',
                            help='Flag for if you\'d like to keep the bundles created in the process of making'
                                 'the content artifacts')

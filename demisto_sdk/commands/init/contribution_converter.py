import json
import os
import re
import shutil
import textwrap
import traceback
import zipfile
from collections import defaultdict
from datetime import datetime
from string import punctuation
from typing import Dict, List, Union

import click

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    AUTOMATION, ENTITY_TYPE_TO_DIR, INTEGRATION, INTEGRATIONS_DIR,
    MARKETPLACE_LIVE_DISCUSSIONS, MARKETPLACES, PACK_INITIAL_VERSION, SCRIPT,
    SCRIPTS_DIR, XSOAR_AUTHOR, XSOAR_SUPPORT, XSOAR_SUPPORT_URL)
from demisto_sdk.commands.common.tools import (LOG_COLORS, capital_case,
                                               find_type,
                                               get_child_directories,
                                               get_child_files,
                                               get_content_path)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.generate_docs.generate_integration_doc import \
    generate_integration_doc
from demisto_sdk.commands.generate_docs.generate_playbook_doc import \
    generate_playbook_doc
from demisto_sdk.commands.generate_docs.generate_script_doc import \
    generate_script_doc
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from demisto_sdk.commands.update_release_notes.update_rn_manager import \
    UpdateReleaseNotesManager


class ContributionConverter:
    """ContributionConverter converts contribution zip files to valid pack formats

    Class Variables:
        DATE_FORMAT (str): The date format to use in the pack metadata

    Instance Variables:
        name (str): The name for the pack
        configuration (Configuration): Configuration instance
        contribution (str|Nonetype): The path to a contribution zip file
        description (str): Description to attach to a converted contribution pack (in pack_metadata.json)
        author (str): Author to ascribe to a pack converted from a contribution zip (in pack_metadata.json)
        contrib_conversion_errs (List[str]): Messages of errors that occurred during a contribution conversion process
        packs_dir_path (str): The path to the 'Packs' subdirectory of the local content repo
        pack_dir_path (str): The path to the specific pack directory being created or updated, e.g. .../Packs/AbuseDB
        dir_name (str): The directory name of a pack's containing folder
        create_new (bool): True if creating a new pack (default), False if updating an existing pack
        gh_user (str): The github username of the person contributing the pack
        readme_files (List[str]): The readme files paths that is generated for new content items.
        update_type (str): The type of update being done. For exiting pack only.
        release_notes (str): The release note text. For exiting pack only.
        detected_content_items (List[str]):
            List of the detected content items objects in the contribution. For exiting pack only.
    """
    DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, name: str = '', contribution: Union[str] = None, description: str = '', author: str = '',
                 gh_user: str = '', create_new: bool = True, pack_dir_name: Union[str] = None, update_type: str = '',
                 release_notes: str = '', detected_content_items: list = None, base_dir: Union[str] = None,
                 no_pipenv: bool = False):
        """Initializes a ContributionConverter instance

        Note that when recieving a contribution that is an update to an existing pack that the values of 'name',
        'description' and 'author' will be those of the existing pack.

        Args:
            name (str, optional): The name of the pack. Defaults to ''.
            contribution (Union[str], optional): The path to the contribution zipfile. Defaults to None.
            description (str, optional): The description for the contribution. Defaults to ''.
            author (str, optional): The author of the contribution. Defaults to ''.
            gh_user (str, optional): The github username of the person contributing. Defaults to ''.
            create_new (bool, optional): Whether the contribution is intended as a new pack. When the contribution is
                intended as an update to an existing pack, the value passed should be False. Defaults to True.
            pack_dir_name (Union[str], optional): Explicitly pass the name of the pack directory. Only useful when
                updating an existing pack and the pack's directory is not equivalent to the value returned from
                running `self.format_pack_dir_name(name)`
            base_dir (Union[str], optional): Used to explicitly pass the path to the top-level directory of the
                local content repo. If no value is passed, the `get_content_path()` function is used to determine
                the path. Defaults to None.

        """
        self.configuration = Configuration()
        self.contribution = contribution
        self.description = description
        self.author = author
        self.update_type = update_type or 'revision'
        self.release_notes = release_notes
        self.detected_content_items = detected_content_items or []
        self.gh_user = gh_user
        self.contrib_conversion_errs: List[str] = []
        self.create_new = create_new
        self.no_pipenv = no_pipenv
        base_dir = base_dir or get_content_path()
        self.packs_dir_path = os.path.join(base_dir, 'Packs')
        if not os.path.isdir(self.packs_dir_path):
            os.makedirs(self.packs_dir_path)

        self.name = name
        self.dir_name = pack_dir_name or ContributionConverter.format_pack_dir_name(name)
        if create_new:
            # make sure that it doesn't conflict with an existing pack directory
            self.dir_name = self.ensure_unique_pack_dir_name(self.dir_name)
        self.pack_dir_path = os.path.join(self.packs_dir_path, self.dir_name)
        if not os.path.isdir(self.pack_dir_path):
            os.makedirs(self.pack_dir_path)
        self.readme_files: List[str] = []

    @staticmethod
    def format_pack_dir_name(name: str) -> str:
        """Formats a (pack) name to a valid value

        Specification:
            A valid pack name does not contain any whitespace and may only contain alphanumeric, underscore, and
            dash characters. The name must begin and end with an alphanumeric character. If it begins with an
            alphabetical character, that character must be capitalized.

        Behavior:
            Individual words are titlecased, whitespace is stripped, and disallowed punctuation and space
            characters are replaced with underscores.

        Args:
            name (str): The proposed pack name to convert to valid pack name format

        Returns:
            str: The reformatted pack name
        """
        temp = capital_case(name.strip().strip('-_'))
        punctuation_to_replace = punctuation.replace('-', '').replace('_', '')
        translation_dict = {x: '_' for x in punctuation_to_replace}
        translation_table = str.maketrans(translation_dict)
        temp = temp.translate(translation_table).strip('-_')
        temp = re.sub(r'-+', '-', re.sub(r'_+', '_', temp))
        comparator = capital_case(temp.replace('_', ' ').replace('-', ' '))
        result = ''
        i = j = 0
        while i < len(temp):
            temp_char = temp[i]
            comp_char = comparator[j]
            if temp_char.casefold() != comp_char.casefold():
                while temp_char in {' ', '_', '-'}:
                    result += f'{temp_char}'
                    i += 1
                    temp_char = temp[i]
                while comp_char in {' '}:
                    j += 1
                    comp_char = comparator[j]
            else:
                result += comparator[j]
                i += 1
                j += 1
        result = result.replace(' ', '')
        result = re.sub(r'-+', '-', re.sub(r'_+', '_', result))
        return result

    def ensure_unique_pack_dir_name(self, pack_dir: str) -> str:
        """When creating a brand new pack, ensures the name used for the pack directory is unique

        If the proposed pack directory name already exists under the 'content/Packs' directory, then
        a 'V2' is appended to the proposed name. If the proposed name already ends with a digit, the
        digit is incremented. The adjusted pack directory name (if the name wasn't already unique)
        is returned.

        Args:
            pack_dir (str): The proposed name of the pack directory

        Returns:
            str: A unique pack directory name
        """
        while os.path.exists(os.path.join(self.packs_dir_path, pack_dir)):
            click.echo(
                f'Modifying pack name because pack {pack_dir} already exists in the content repo',
                color=LOG_COLORS.NATIVE
            )
            if len(pack_dir) >= 2 and pack_dir[-2].lower() == 'v' and pack_dir[-1].isdigit():
                # increment by one
                pack_dir = pack_dir[:-1] + str(int(pack_dir[-1]) + 1)
            else:
                pack_dir += 'V2'
            click.echo(f'New pack name is "{pack_dir}"', color=LOG_COLORS.NATIVE)
        return pack_dir

    def unpack_contribution_to_dst_pack_directory(self) -> None:
        """Unpacks the contribution zip's contents to the destination pack directory and performs some cleanup"""
        if self.contribution:
            shutil.unpack_archive(filename=self.contribution, extract_dir=self.pack_dir_path)
            # remove metadata.json file
            os.remove(os.path.join(self.pack_dir_path, 'metadata.json'))
        else:
            err_msg = ('Tried unpacking contribution to destination directory but the instance variable'
                       ' "contribution" is "None" - Make sure "contribution" is set before trying to unpack'
                       ' the contribution.')
            raise TypeError(err_msg)

    def convert_contribution_dir_to_pack_contents(self, unpacked_contribution_dir: str) -> None:
        """Converts a directory and its contents unpacked from the contribution zip file to the appropriate structure

        Example:
            The pack directory after `unpack_contribution_to_dst_pack_directory` has been executed:

            ExamplePack
            ├── automation
            │   └── automation-ExampleAutomation.yml
            ├── integration
            │   └── integration-ExampleIntegration.yml
            ├── playbook
            │   └── playbook-ExamplePlaybook.yml
            ├── report
            │   └── report-ExampleReport.json
            └── reputation
                └── reputation-ExampleReputation.json

            The updated pack directory structure after `convert_contribution_dir_to_pack_contents` has been
            executed, passing the path of .../ExamplePack/integration as the argument, would appear as so:

            ExamplePack
            ├── automation
            │   └── automation-ExampleAutomation.yml
            ├── Integrations
            │   └── integration-ExampleIntegration.yml
            ├── playbook
            │   └── playbook-ExamplePlaybook.yml
            ├── report
            │   └── report-ExampleReport.json
            └── reputation
                └── reputation-ExampleReputation.json

        Args:
            unpacked_contribution_dir (str): The directory to convert
        """
        basename = os.path.basename(unpacked_contribution_dir)
        if basename in ENTITY_TYPE_TO_DIR:
            dst_name = ENTITY_TYPE_TO_DIR.get(basename, '')
            src_path = os.path.join(self.pack_dir_path, basename)
            dst_path = os.path.join(self.pack_dir_path, dst_name)
            if os.path.exists(dst_path):
                # move src folder files to dst folder
                for _, _, files in os.walk(src_path, topdown=False):
                    for name in files:
                        src_file_path = os.path.join(src_path, name)
                        dst_file_path = os.path.join(dst_path, name)
                        shutil.move(src_file_path, dst_file_path)
                shutil.rmtree(src_path, ignore_errors=True)
            else:
                # replace dst folder with src folder
                shutil.move(src_path, dst_path)

    def format_converted_pack(self) -> None:
        """Runs the demisto-sdk's format command on the pack converted from the contribution zipfile"""
        click.echo(
            f'Executing \'format\' on the restructured contribution zip new/modified files at {self.pack_dir_path}'
        )
        from_version = '6.0.0' if self.create_new else ''
        print(f'This is the pack dir path: {self.pack_dir_path}')
        format_manager(
            from_version=from_version,
            no_validate=True,
            update_docker=True,
            verbose=True,
            assume_yes=True,
        )

    def generate_readme_for_pack_content_item(self, yml_path: str) -> None:
        """ Runs the demisto-sdk's generate-docs command on a pack content item

        Args:
            yml_path: str: Content item yml path.
        """
        file_type = find_type(yml_path)
        file_type = file_type.value if file_type else file_type
        if file_type == 'integration':
            generate_integration_doc(yml_path)
        if file_type == 'script':
            generate_script_doc(input_path=yml_path, examples=[])
        if file_type == 'playbook':
            generate_playbook_doc(yml_path)

        dir_output = os.path.dirname(os.path.realpath(yml_path))
        readme_path = os.path.join(dir_output, 'README.md')
        self.readme_files.append(readme_path)

    def generate_readmes_for_new_content_pack(self):
        """
        Generate the readme files for a new content pack.
        """
        for pack_subdir in get_child_directories(self.pack_dir_path):
            basename = os.path.basename(pack_subdir)
            if basename in {SCRIPTS_DIR, INTEGRATIONS_DIR}:
                directories = get_child_directories(pack_subdir)
                for directory in directories:
                    files = get_child_files(directory)
                    for file in files:
                        file_name = os.path.basename(file)
                        if file_name.startswith('integration-') \
                                or file_name.startswith('script-') \
                                or file_name.startswith('automation-'):
                            unified_file = file
                            self.generate_readme_for_pack_content_item(unified_file)
                            os.remove(unified_file)
            elif basename == 'Playbooks':
                files = get_child_files(pack_subdir)
                for file in files:
                    file_name = os.path.basename(file)
                    if file_name.startswith('playbook') and file_name.endswith('.yml'):
                        self.generate_readme_for_pack_content_item(file)

    def convert_contribution_to_pack(self, files_to_source_mapping: Dict = None):
        """Create or updates a pack in the content repo from the contents of a contribution zipfile

        Args:
            files_to_source_mapping (Dict[str, Dict[str, str]]): Only used when updating a pack. mapping of a file
                name as inside the the contribution zip to a dictionary containing the the associated source info
                for that file, specifically the base name (the name used in naming the split component files) and
                the name of the containing directory.
        """
        try:
            # only create pack_metadata.json and base pack files if creating a new pack
            if self.create_new:
                if self.contribution:
                    # create pack metadata file
                    with zipfile.ZipFile(self.contribution) as zipped_contrib:
                        with zipped_contrib.open('metadata.json') as metadata_file:
                            click.echo(f'Pulling relevant information from {metadata_file.name}',
                                       color=LOG_COLORS.NATIVE)
                            metadata = json.loads(metadata_file.read())
                            self.create_metadata_file(metadata)
                # create base files
                self.create_pack_base_files()
            # unpack
            self.unpack_contribution_to_dst_pack_directory()
            # convert
            unpacked_contribution_dirs = get_child_directories(self.pack_dir_path)
            for unpacked_contribution_dir in unpacked_contribution_dirs:
                self.convert_contribution_dir_to_pack_contents(unpacked_contribution_dir)
            # extract to package format
            for pack_subdir in get_child_directories(self.pack_dir_path):
                basename = os.path.basename(pack_subdir)
                if basename in {SCRIPTS_DIR, INTEGRATIONS_DIR}:
                    self.content_item_to_package_format(
                        pack_subdir, del_unified=(not self.create_new), source_mapping=files_to_source_mapping
                    )

            if self.create_new:
                self.generate_readmes_for_new_content_pack()

            # format
            self.format_converted_pack()
        except Exception as e:
            click.echo(
                f'Creating a Pack from the contribution zip failed with error: {e}\n {traceback.format_exc()}',
                color=LOG_COLORS.RED
            )
        finally:
            if self.contrib_conversion_errs:
                click.echo(
                    'The following errors occurred while converting unified content YAMLs to package structure:'
                )
                click.echo(
                    textwrap.indent('\n'.join(self.contrib_conversion_errs), '\t')
                )

    def content_item_to_package_format(self, content_item_dir: str, del_unified: bool = True,
                                       source_mapping: Union[Dict[str, Dict[str, str]]] = None):
        """
        Iterate over the YAML files in a directory and create packages (a containing directory and
        component files) from the YAMLs of integrations and scripts

        Args:
            content_item_dir (str): Path to the directory containing the content item YAML file(s)
            del_unified (bool): Whether to delete the unified yaml the package was extracted from
            source_mapping (Union[Dict], optional): Can be used when updating an existing pack and
                the package directory of a content item is not what would ordinarily be set by the
                `demisto-sdk` `split` command. Sample value would be,
                `{'integration-AbuseIPDB.yml': {'containing_dir_name': 'AbuseDB', 'base_name': 'AbuseDB'}}`
                - the split command would create a containing directory of `AbuseIPDB` for the file
                `integration-AbuseIPDB.yml` and we need the containing directory of the package to match
                what already exists in the repo.
        """
        child_files = get_child_files(content_item_dir)
        for child_file in child_files:
            cf_name_lower = os.path.basename(child_file).lower()
            if cf_name_lower.startswith((SCRIPT, AUTOMATION, INTEGRATION)) and cf_name_lower.endswith('yml'):
                content_item_file_path = child_file
                file_type = find_type(content_item_file_path)
                file_type = file_type.value if file_type else file_type
                try:
                    child_file_name = os.path.basename(child_file)
                    if source_mapping and child_file_name in source_mapping.keys():
                        child_file_mapping = source_mapping.get(child_file_name, {})
                        base_name = child_file_mapping.get('base_name', '')
                        containing_dir_name = child_file_mapping.get('containing_dir_name', '')
                        # for legacy unified yamls in the repo, their containing directory will be that of their
                        # entity type directly instead of the typical package format. For those cases, we need the
                        # extractor to auto create the containing directory. An example would be -
                        # 'content/Packs/AbuseDB/Scripts/script-AbuseIPDBPopulateIndicators.yml'
                        autocreate_dir = containing_dir_name == ENTITY_TYPE_TO_DIR.get(file_type, '')
                        output_dir = os.path.join(self.pack_dir_path, ENTITY_TYPE_TO_DIR.get(file_type, ''))
                        if not autocreate_dir:
                            output_dir = os.path.join(output_dir, containing_dir_name)
                        os.makedirs(output_dir, exist_ok=True)
                        extractor = YmlSplitter(input=content_item_file_path, file_type=file_type, output=output_dir,
                                                no_readme=True, base_name=base_name,
                                                no_auto_create_dir=(not autocreate_dir), no_pipenv=self.no_pipenv)

                    else:
                        extractor = YmlSplitter(input=content_item_file_path, file_type=file_type,
                                                output=content_item_dir, no_pipenv=self.no_pipenv)
                    extractor.extract_to_package_format()
                except Exception as e:
                    err_msg = f'Error occurred while trying to split the unified YAML "{content_item_file_path}" ' \
                              f'into its component parts.\nError: "{e}"'
                    self.contrib_conversion_errs.append(err_msg)
                finally:
                    output_path = extractor.get_output_path()
                    if self.create_new:
                        # Moving the unified file to its package.
                        shutil.move(content_item_file_path, output_path)
                    if del_unified:
                        if os.path.exists(content_item_file_path):
                            os.remove(content_item_file_path)
                        moved_unified_dst = os.path.join(output_path, child_file_name)
                        if os.path.exists(moved_unified_dst):
                            os.remove(moved_unified_dst)

    def create_pack_base_files(self):
        """
        Create empty 'README.md', '.secrets-ignore', and '.pack-ignore' files that are expected
        to be in the base directory of a pack
        """
        click.echo('Creating pack base files', color=LOG_COLORS.NATIVE)
        fp = open(os.path.join(self.pack_dir_path, 'README.md'), 'a')
        fp.close()

        fp = open(os.path.join(self.pack_dir_path, '.secrets-ignore'), 'a')
        fp.close()

        fp = open(os.path.join(self.pack_dir_path, '.pack-ignore'), 'a')
        fp.close()

    def create_metadata_file(self, zipped_metadata: Dict) -> None:
        """Create the pack_metadata.json file in the base directory of the pack

        Args:
            zipped_metadata (Dict): The metadata that came in the zipfile
        """
        metadata_dict = {}

        # a description passed on the cmd line should take precedence over one pulled
        # from contribution metadata
        metadata_dict['description'] = self.description or zipped_metadata.get('description')
        metadata_dict['name'] = self.name
        metadata_dict['author'] = self.author or zipped_metadata.get('author', '')
        metadata_dict['support'] = 'community'
        metadata_dict['url'] = zipped_metadata.get('supportDetails', {}).get('url', MARKETPLACE_LIVE_DISCUSSIONS)
        metadata_dict['categories'] = zipped_metadata.get('categories') if zipped_metadata.get('categories') else []
        metadata_dict['tags'] = zipped_metadata.get('tags') if zipped_metadata.get('tags') else []
        metadata_dict['useCases'] = zipped_metadata.get('useCases') if zipped_metadata.get('useCases') else []
        metadata_dict['keywords'] = zipped_metadata.get('keywords') if zipped_metadata.get('keywords') else []
        metadata_dict['githubUser'] = [self.gh_user] if self.gh_user else []
        metadata_dict['marketplaces'] = zipped_metadata.get('marketplaces') or MARKETPLACES
        metadata_dict = ContributionConverter.create_pack_metadata(data=metadata_dict)
        metadata_path = os.path.join(self.pack_dir_path, 'pack_metadata.json')
        with open(metadata_path, 'w') as pack_metadata_file:
            json.dump(metadata_dict, pack_metadata_file, indent=4)

    @staticmethod
    def create_pack_metadata(data: Dict = None) -> Dict:
        """Builds pack metadata JSON content.

        Args:
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
            'created': datetime.utcnow().strftime(ContributionConverter.DATE_FORMAT),
            'categories': [],
            'tags': [],
            'useCases': [],
            'keywords': [],
            'marketplaces': [],
        }

        if data:
            pack_metadata.update(data)

        return pack_metadata

    def execute_update_rn(self):
        """
        Bump the pack version in the pack metadata according to the update type
        and create a release-note file using the release-notes text.

        """
        rn_mng = UpdateReleaseNotesManager(user_input=self.dir_name, update_type=self.update_type, )
        rn_mng.manage_rn_update()
        self.replace_RN_template_with_value(rn_mng.rn_path[0])

    def format_user_input(self) -> Dict[str, str]:
        """
        Replace the content item name with the content item display name if exists
        to match the template that being generated by the UpdateRN class by calling
        UpdateRN class function get_display_name(file_path)

        Build a dictionary with the release notes text per content item detected.

        Returns:
            Dict: Key is content item name, value is release note entry
        """
        entity_identifier = '##### '
        content_item_type_identifier = '#### '
        rn_per_content_item: dict = defaultdict(str)
        entity_name = 'NonEntityRelated'

        items_path = {content_item.get('source_id'): content_item.get('source_file_name')
                      for content_item in self.detected_content_items}

        for line in filter(None, self.release_notes.splitlines()):
            if line.startswith(entity_identifier):
                entity_name = line.lstrip(entity_identifier)
                if items_path.get(entity_name):
                    entity_name = UpdateRN.get_display_name(items_path.get(entity_name))
            elif not line.startswith(content_item_type_identifier):
                rn_per_content_item[entity_name] = rn_per_content_item[entity_name] + line + '\n'
        return rn_per_content_item

    def replace_RN_template_with_value(self, rn_path: str):
        """
        Replace the release notes template for a given release-note file path
        with the contributor's text.
        Will only affect the detected content items template text.
        New items rn entries and updated docker image entries for the detected items won't get changed.

        Args:
            rn_path: path to the rn file created.
        """
        entity_identifier = '##### '
        template_text = '%%UPDATE_RN%%'

        rn_per_content_item = self.format_user_input()

        with open(rn_path, 'r+') as rn_file:
            lines = rn_file.readlines()
            for index in range(len(lines)):
                if template_text in lines[index]:
                    template_entity = lines[index - 1].lstrip(entity_identifier).rstrip('\n')
                    curr_content_items = rn_per_content_item.get(template_entity)
                    if curr_content_items:
                        lines[index] = curr_content_items

            rn_file.seek(0)
            rn_file.writelines(lines)
            rn_file.truncate()

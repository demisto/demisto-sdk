"""
This module is designed to validate the existence and structure of content pack essential files in content.
"""
import io
import json
import os
import re
from datetime import datetime
from distutils.version import LooseVersion
from pathlib import Path

import click
from dateutil import parser
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (  # PACK_METADATA_PRICE,
    API_MODULES_PACK, PACK_METADATA_CATEGORIES, PACK_METADATA_CERTIFICATION,
    PACK_METADATA_CREATED, PACK_METADATA_DEPENDENCIES, PACK_METADATA_DESC,
    PACK_METADATA_EMAIL, PACK_METADATA_FIELDS, PACK_METADATA_KEYWORDS,
    PACK_METADATA_NAME, PACK_METADATA_SUPPORT, PACK_METADATA_TAGS,
    PACK_METADATA_URL, PACK_METADATA_USE_CASES, PACKS_PACK_IGNORE_FILE_NAME,
    PACKS_PACK_META_FILE_NAME, PACKS_README_FILE_NAME,
    PACKS_WHITELIST_FILE_NAME)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (get_json, get_remote_file,
                                               pack_name_to_path)
from demisto_sdk.commands.find_dependencies.find_dependencies import \
    PackDependencies
from git import GitCommandError, Repo

CONTRIBUTORS_LIST = ['partner', 'developer', 'community']
SUPPORTED_CONTRIBUTORS_LIST = ['partner', 'developer']
ISO_TIMESTAMP_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
ALLOWED_CERTIFICATION_VALUES = ['certified', 'verified']
SUPPORT_TYPES = ['community', 'xsoar'] + SUPPORTED_CONTRIBUTORS_LIST


class PackUniqueFilesValidator(BaseValidator):
    """PackUniqueFilesValidator is designed to validate the correctness of content pack's files structure.
    Existence and validity of this files is essential."""

    def __init__(self, pack, pack_path=None, validate_dependencies=False, ignored_errors=None, print_as_warnings=False,
                 should_version_raise=False, id_set_path=None, suppress_print=False, private_repo=False,
                 skip_id_set_creation=False):
        """Inits the content pack validator with pack's name, pack's path, and unique files to content packs such as:
        secrets whitelist file, pack-ignore file, pack-meta file and readme file
        :param pack: content package name, which is the directory name of the pack
        """
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print)
        self.pack = pack
        self.pack_path = pack_name_to_path(self.pack) if not pack_path else pack_path
        self.secrets_file = PACKS_WHITELIST_FILE_NAME
        self.pack_ignore_file = PACKS_PACK_IGNORE_FILE_NAME
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.readme_file = PACKS_README_FILE_NAME
        self.validate_dependencies = validate_dependencies
        self._errors = []
        self.should_version_raise = should_version_raise
        self.id_set_path = id_set_path
        self.private_repo = private_repo
        self.skip_id_set_creation = skip_id_set_creation

    # error handling
    def _add_error(self, error, file_path):
        """Adds error entry to a list under pack's name
        Returns True if added and false otherwise"""
        error_message, error_code = error

        if self.pack_path not in file_path:
            file_path = os.path.join(self.pack_path, file_path)

        formatted_error = self.handle_error(error_message, error_code, file_path=file_path, should_print=False)
        if formatted_error:
            self._errors.append(formatted_error)
            return True

        return False

    def get_errors(self, raw=False) -> str:
        """Get the dict version or string version for print"""
        errors = ''
        if raw:
            errors = '\n  '.join(self._errors)
        elif self._errors:
            errors = ' - Issues with unique files in pack: {}\n  {}'.format(self.pack, '\n  '.join(self._errors))

        return errors

    # file utils
    def _get_pack_file_path(self, file_name=''):
        """Returns the full file path to pack's file"""
        return os.path.join(self.pack_path, file_name)

    def _is_pack_file_exists(self, file_name):
        """Check if .secrets-ignore exists"""
        if not os.path.isfile(self._get_pack_file_path(file_name)):
            if self._add_error(Errors.pack_file_does_not_exist(file_name), file_name):
                return False

        return True

    def _read_file_content(self, file_name):
        """Open & Read a file object's content throw exception if can't"""
        try:
            with io.open(self._get_pack_file_path(file_name), mode="r", encoding="utf-8") as file:
                return file.read()
        except IOError:
            if not self._add_error(Errors.cant_open_pack_file(file_name), file_name):
                return "No-Text-Required"
        except ValueError:
            if not self._add_error(Errors.cant_read_pack_file(file_name), file_name):
                return "No-Text-Required"

        return False

    def _parse_file_into_list(self, file_name, delimiter='\n'):
        """Parse file's content to list, throw exception if can't"""
        file_content = self._read_file_content(file_name)
        try:
            if file_content:
                return file_content.split(delimiter)
        except ValueError:
            if not self._add_error(Errors.cant_parse_pack_file_to_list(file_name), file_name):
                return True

        return False

    @staticmethod
    def check_timestamp_format(timestamp):
        """Check that the timestamp is in ISO format"""
        try:
            datetime.strptime(timestamp, ISO_TIMESTAMP_FORMAT)
            return True
        except ValueError:
            return False

    # secrets validation
    def validate_secrets_file(self):
        """Validate everything related to .secrets-ignore file"""
        if self._is_pack_file_exists(self.secrets_file) and all([self._is_secrets_file_structure_valid()]):
            return True

        return False

    def _is_secrets_file_structure_valid(self):
        """Check if .secrets-ignore structure is parse-able"""
        if self._parse_file_into_list(self.secrets_file):
            return True

        return False

    # pack ignore validation
    def validate_pack_ignore_file(self):
        """Validate everything related to .pack-ignore file"""
        if self._is_pack_file_exists(self.pack_ignore_file) and all([self._is_pack_ignore_file_structure_valid()]):
            return True

        return False

    def _is_pack_ignore_file_structure_valid(self):
        """Check if .pack-ignore structure is parse-able"""
        try:
            if self._parse_file_into_list(self.pack_ignore_file):
                return True
        except re.error:
            if not self._add_error(Errors.pack_file_bad_format(self.pack_ignore_file), self.pack_ignore_file):
                return True

        return False

    # pack metadata validation
    def validate_pack_meta_file(self):
        """Validate everything related to pack_metadata.json file"""
        if self._is_pack_file_exists(self.pack_meta_file) and all([
            self._is_pack_meta_file_structure_valid(),
            self._is_valid_contributor_pack_support_details(),
            self._is_approved_usecases(),
            self._is_approved_tags(),
            self._is_price_changed(),
            self._is_approved_tags(),
            self._is_valid_support_type()
        ]):
            if self.should_version_raise:
                return self.validate_version_bump()

            else:
                return True

        return False

    def validate_version_bump(self):
        metadata_file_path = self._get_pack_file_path(self.pack_meta_file)
        old_meta_file_content = get_remote_file(metadata_file_path)
        current_meta_file_content = get_json(metadata_file_path)
        old_version = old_meta_file_content.get('currentVersion', '0.0.0')
        current_version = current_meta_file_content.get('currentVersion', '0.0.0')
        if LooseVersion(old_version) < LooseVersion(current_version):
            return True

        elif self._add_error(Errors.pack_metadata_version_should_be_raised(self.pack, old_version), metadata_file_path):
            return False

        return True

    def _is_pack_meta_file_structure_valid(self):
        """Check if pack_metadata.json structure is json parse-able and valid"""
        try:
            pack_meta_file_content = self._read_file_content(self.pack_meta_file)
            if not pack_meta_file_content:
                if self._add_error(Errors.pack_metadata_empty(), self.pack_meta_file):
                    return False

            metadata = json.loads(pack_meta_file_content)
            if not isinstance(metadata, dict):
                if self._add_error(Errors.pack_metadata_should_be_dict(self.pack_meta_file), self.pack_meta_file):
                    return False

            missing_fields = [field for field in PACK_METADATA_FIELDS if field not in metadata.keys()]
            if missing_fields:
                if self._add_error(Errors.missing_field_iin_pack_metadata(self.pack_meta_file, missing_fields),
                                   self.pack_meta_file):
                    return False

            # check validity of pack metadata mandatory fields
            name_field = metadata.get(PACK_METADATA_NAME, '').lower()
            if not name_field or 'fill mandatory field' in name_field:
                if self._add_error(Errors.pack_metadata_name_not_valid(), self.pack_meta_file):
                    return False

            description_name = metadata.get(PACK_METADATA_DESC, '').lower()
            if not description_name or 'fill mandatory field' in description_name:
                if self._add_error(Errors.pack_metadata_field_invalid(), self.pack_meta_file):
                    return False

            # check non mandatory dependency field
            dependencies_field = metadata.get(PACK_METADATA_DEPENDENCIES, {})
            if not isinstance(dependencies_field, dict):
                if self._add_error(Errors.dependencies_field_should_be_dict(self.pack_meta_file), self.pack_meta_file):
                    return False

            # check created field in iso format
            created_field = metadata.get(PACK_METADATA_CREATED, '')
            if created_field:
                if not self.check_timestamp_format(created_field):
                    suggested_value = parser.parse(created_field).isoformat() + "Z"
                    if self._add_error(
                            Errors.pack_timestamp_field_not_in_iso_format(PACK_METADATA_CREATED,
                                                                          created_field, suggested_value),
                            self.pack_meta_file):
                        return False

            # check metadata list fields and validate that no empty values are contained in this fields
            for list_field in (PACK_METADATA_KEYWORDS, PACK_METADATA_TAGS, PACK_METADATA_CATEGORIES,
                               PACK_METADATA_USE_CASES):
                field = metadata[list_field]
                if field and len(field) == 1:
                    value = field[0]
                    if not value:
                        if self._add_error(Errors.empty_field_in_pack_metadata(self.pack_meta_file, list_field),
                                           self.pack_meta_file):
                            return False

            # if the field 'certification' exists, check that its value is set to 'certified' or 'verified'
            certification = metadata.get(PACK_METADATA_CERTIFICATION)
            if certification and certification not in ALLOWED_CERTIFICATION_VALUES:
                if self._add_error(Errors.pack_metadata_certification_is_invalid(self.pack_meta_file),
                                   self.pack_meta_file):
                    return False

        except (ValueError, TypeError):
            if self._add_error(Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file):
                return False

        return True

    def _is_valid_contributor_pack_support_details(self):
        """Checks if email or url exist in contributed pack details."""
        try:
            pack_meta_file_content = json.loads(self._read_file_content(self.pack_meta_file))
            if pack_meta_file_content[PACK_METADATA_SUPPORT] in SUPPORTED_CONTRIBUTORS_LIST:
                if not pack_meta_file_content[PACK_METADATA_URL] and not pack_meta_file_content[PACK_METADATA_EMAIL]:
                    if self._add_error(Errors.pack_metadata_missing_url_and_email(), self.pack_meta_file):
                        return False

        except (ValueError, TypeError):
            if self._add_error(Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file):
                return False

        return True

    def _is_valid_support_type(self) -> bool:
        """Checks whether the support type is valid in the pack metadata.

        Returns:
            bool: True if the support type is valid, otherwise False

        """
        try:
            pack_meta_file_content = json.loads(self._read_file_content(self.pack_meta_file))
            if pack_meta_file_content[PACK_METADATA_SUPPORT] not in SUPPORT_TYPES:
                self._add_error(Errors.pack_metadata_invalid_support_type(self.pack_meta_file), self.pack_meta_file)
                return False

        except (ValueError, TypeError):
            if self._add_error(Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file):
                return False

        return True

    def _is_approved_usecases(self) -> bool:
        """Checks whether the usecases in the pack metadata are approved

        Return:
             bool: True if the usecases are approved, otherwise False
        """
        non_approved_usecases = set()
        try:
            approved_usecases = tools.get_remote_file(
                'Tests/Marketplace/approved_usecases.json').get('approved_list') or []
            pack_meta_file_content = json.loads(self._read_file_content(self.pack_meta_file))
            non_approved_usecases = set(pack_meta_file_content[PACK_METADATA_USE_CASES]) - set(approved_usecases)
            if non_approved_usecases:
                if self._add_error(
                        Errors.pack_metadata_non_approved_usecases(non_approved_usecases), self.pack_meta_file):
                    return False
        except (ValueError, TypeError):
            if self._add_error(Errors.pack_metadata_non_approved_usecases(non_approved_usecases), self.pack_meta_file):
                return False
        return True

    def _is_approved_tags(self) -> bool:
        """Checks whether the tags in the pack metadata are approved

        Return:
             bool: True if the tags are approved, otherwise False
        """
        non_approved_tags = set()
        try:
            approved_tags = tools.get_remote_file('Tests/Marketplace/approved_tags.json').get('approved_list') or []
            pack_meta_file_content = json.loads(self._read_file_content(self.pack_meta_file))
            non_approved_tags = set(pack_meta_file_content[PACK_METADATA_TAGS]) - set(approved_tags)
            if non_approved_tags:
                if self._add_error(Errors.pack_metadata_non_approved_tags(non_approved_tags), self.pack_meta_file):
                    return False
        except (ValueError, TypeError):
            if self._add_error(Errors.pack_metadata_non_approved_tags(non_approved_tags), self.pack_meta_file):
                return False
        return True

    def get_master_private_repo_meta_file(self, metadata_file_path: str):
        current_repo = Repo(Path.cwd(), search_parent_directories=True)

        # if running on master branch in private repo - do not run the test
        if current_repo.active_branch == 'master':
            if not self.suppress_print:
                click.secho("Running on master branch - skipping price change validation", fg="yellow")
            return None
        try:
            old_meta_file_content = current_repo.git.show(f'origin/master:{metadata_file_path}')

        except GitCommandError as e:
            if not self.suppress_print:
                click.secho(f"Got an error while trying to connect to git - {str(e)}\n"
                            f"Skipping price change validation")
            return None

        # if there was no past version
        if not old_meta_file_content:
            if not self.suppress_print:
                click.secho("Unable to find previous pack_metadata.json file - skipping price change validation",
                            fg="yellow")
            return None

        return json.loads(old_meta_file_content)

    def _is_price_changed(self) -> bool:
        # only check on private repo
        if not self.private_repo:
            return True

        metadata_file_path = self._get_pack_file_path(self.pack_meta_file)
        old_meta_file_content = self.get_master_private_repo_meta_file(metadata_file_path)

        # if there was no past version or running on master branch
        if not old_meta_file_content:
            return True

        current_meta_file_content = get_json(metadata_file_path)
        current_price = current_meta_file_content.get('price')
        old_price = old_meta_file_content.get('price')

        # if a price was added, removed or changed compared to the master version - return an error
        if (old_price and not current_price) or (current_price and not old_price) or (old_price != current_price):
            if self._add_error(Errors.pack_metadata_price_change(old_price, current_price), self.pack_meta_file):
                return False

        return True

    def validate_pack_unique_files(self) -> str:
        """Main Execution Method"""
        self.validate_secrets_file()
        self.validate_pack_ignore_file()
        # We don't want to check the metadata file for this pack
        if API_MODULES_PACK not in self.pack:
            self.validate_pack_meta_file()
        # We only check pack dependencies for -g flag
        if self.validate_dependencies:
            self.validate_pack_dependencies(id_set_path=self.id_set_path)
        return self.get_errors()

    # pack dependencies validation
    def validate_pack_dependencies(self, id_set_path=None):
        try:
            click.secho(f'\nRunning pack dependencies validation on {self.pack}\n',
                        fg="bright_cyan")
            core_pack_list = tools.get_remote_file('Tests/Marketplace/core_packs_list.json') or []

            first_level_dependencies = PackDependencies.find_dependencies(
                self.pack, id_set_path=id_set_path, silent_mode=True, exclude_ignored_dependencies=False,
                update_pack_metadata=False, skip_id_set_creation=self.skip_id_set_creation
            )

            if not first_level_dependencies:
                if not self.suppress_print:
                    click.secho("Unable to find id_set.json file - skipping dependencies check", fg="yellow")
                return True

            for core_pack in core_pack_list:
                first_level_dependencies.pop(core_pack, None)
            if not first_level_dependencies:
                return True

            dependency_result = json.dumps(first_level_dependencies, indent=4)
            click.echo(click.style(f"Found dependencies result for {self.pack} pack:", bold=True))
            click.echo(click.style(dependency_result, bold=True))
            non_supported_pack = first_level_dependencies.get('NonSupported', {})
            deprecated_pack = first_level_dependencies.get('DeprecatedContent', {})

            if (non_supported_pack.get('mandatory')) or (deprecated_pack.get('mandatory')):
                error_message, error_code = Errors.invalid_package_dependencies(self.pack)
                if self._add_error((error_message, error_code), file_path=self.pack_path):
                    return False
            return True
        except ValueError as e:
            if "Couldn't find any items for pack" in str(e):
                error_message, error_code = Errors.invalid_id_set()
                if self._add_error((error_message, error_code), file_path=self.pack_path):
                    return False
                return True
            else:
                raise

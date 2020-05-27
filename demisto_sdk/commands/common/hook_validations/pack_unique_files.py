"""
This module is designed to validate the existence and structure of content pack essential files in content.
"""
import io
import json
import os
import re

from demisto_sdk.commands.common.constants import (  # PACK_METADATA_PRICE,
    API_MODULES_PACK, PACK_METADATA_CATEGORIES, PACK_METADATA_DEPENDENCIES,
    PACK_METADATA_DESC, PACK_METADATA_FIELDS, PACK_METADATA_KEYWORDS,
    PACK_METADATA_NAME, PACK_METADATA_TAGS, PACK_METADATA_USE_CASES,
    PACKS_PACK_IGNORE_FILE_NAME, PACKS_PACK_META_FILE_NAME,
    PACKS_README_FILE_NAME, PACKS_WHITELIST_FILE_NAME)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import pack_name_to_path


class PackUniqueFilesValidator(BaseValidator):
    """PackUniqueFilesValidator is designed to validate the correctness of content pack's files structure.
    Existence and validity of this files is essential."""

    def __init__(self, pack, ignored_errors=None, print_as_warnings=False):
        """Inits the content pack validator with pack's name, pack's path, and unique files to content packs such as:
        secrets whitelist file, pack-ignore file, pack-meta file and readme file
        :param pack: content package name, which is the directory name of the pack
        """
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
        self.pack = pack
        self.pack_path = pack_name_to_path(self.pack)
        self.secrets_file = PACKS_WHITELIST_FILE_NAME
        self.pack_ignore_file = PACKS_PACK_IGNORE_FILE_NAME
        self.pack_meta_file = PACKS_PACK_META_FILE_NAME
        self.readme_file = PACKS_README_FILE_NAME
        self._errors = []

    # error handling
    def _add_error(self, error, file_path):
        """Adds error entry to a list under pack's name
        Returns True if added and false otherwise"""
        error_message, error_code = error
        formatted_error = self.handle_error(error_message, error_code, file_path=file_path, should_print=False)
        if formatted_error:
            self._errors.append(formatted_error)
            return True

        return False

    def get_errors(self, raw=False):
        """Get the dict version or string version for print"""
        errors = ''
        if raw:
            errors = self._errors
        elif self._errors:
            errors = '@@@Issues with unique files in pack: {}\n  {}'.format(self.pack, '\n  '.join(self._errors))

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
        if self._is_pack_file_exists(self.pack_meta_file) and all([self._is_pack_meta_file_structure_valid()]):
            return True

        return False

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
        except (ValueError, TypeError):
            if self._add_error(Errors.pack_metadata_isnt_json(self.pack_meta_file), self.pack_meta_file):
                return False

        return True

    # pack README.md validation
    def validate_readme_file(self):
        """Validate everything related to README.md file"""
        if self._is_pack_file_exists(self.readme_file):
            return True

        return False

    def validate_pack_unique_files(self):
        """Main Execution Method"""
        self.validate_secrets_file()
        self.validate_pack_ignore_file()
        self.validate_readme_file()
        # We don't want to check the metadata file for this pack
        if API_MODULES_PACK not in self.pack:
            self.validate_pack_meta_file()

        return self.get_errors()

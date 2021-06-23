import os
import re
from typing import Optional

from demisto_sdk.commands.common.constants import (API_MODULES_PACK,
                                                   DEPRECATED_REGEXES,
                                                   PYTHON_SUBTYPES, TYPE_PWSH)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.tools import (
    get_core_pack_list, get_file_version_suffix_if_exists, get_files_in_dir,
    get_pack_name, server_version_compare)


class ScriptValidator(ContentEntityValidator):
    """ScriptValidator is designed to validate the correctness of the file structure we enter to content repo. And
        also try to catch possible Backward compatibility breaks due to the preformed changes.
    """

    def is_valid_version(self) -> bool:
        if self.current_file.get('commonfields', {}).get('version') != self.DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    @classmethod
    def _is_sub_set(cls, supposed_bigger_list, supposed_smaller_list):
        # type: (list, list) -> bool
        """Check if supposed_smaller_list is a subset of the supposed_bigger_list"""
        for check_item in supposed_smaller_list:
            if check_item not in supposed_bigger_list:
                return False
        return True

    def is_backward_compatible(self):
        # type: () -> bool
        """Check if the script is backward compatible."""
        if not self.old_file:
            return True

        is_breaking_backwards = [
            self.is_context_path_changed(),
            self.is_added_required_args(),
            self.is_arg_changed(),
            self.is_there_duplicates_args(),
            self.is_changed_subtype()
        ]

        # Add sane-doc-report exception
        # Sane-doc-report uses docker and every fix/change requires a docker tag change,
        # thus it won't be backwards compatible.
        # All other tests should be False (i.e. no problems)
        if self.file_path == 'Scripts/SaneDocReport/SaneDocReport.yml':
            return not any(is_breaking_backwards[1:])
        return not any(is_breaking_backwards)

    def is_valid_file(self, validate_rn=True):
        # type: (bool) -> bool
        """Check whether the script is valid or not"""
        is_script_valid = all([
            super().is_valid_file(validate_rn),
            self.is_valid_subtype(),
            self.is_id_equals_name(),
            self.is_docker_image_valid(),
            self.is_valid_pwsh(),
            self.is_valid_script_file_path(),
            self.is_there_separators_in_names(),
            self.name_not_contain_the_type()
        ])
        # check only on added files
        if not self.old_file:
            is_script_valid = all([
                is_script_valid,
                self.is_valid_name()
            ])
        core_packs_list = get_core_pack_list()

        pack = get_pack_name(self.file_path)
        is_core = True if pack in core_packs_list else False
        if is_core:
            is_script_valid = all([
                is_script_valid,
                self.no_incident_in_core_pack()
            ])
        return is_script_valid

    @classmethod
    def _get_arg_to_required_dict(cls, script_json):
        """Get a dictionary arg name to its required status.

        Args:
            script_json (dict): Dictionary of the examined script.

        Returns:
            dict. arg name to its required status.
        """
        arg_to_required = {}
        args = script_json.get('args', [])
        for arg in args:
            arg_to_required[arg.get('name')] = arg.get('required', False)
        return arg_to_required

    def is_changed_subtype(self):
        """Validate that the subtype was not changed."""
        type_ = self.current_file.get('type')
        if type_ == 'python':
            subtype = self.current_file.get('subtype')
            if self.old_file:
                old_subtype = self.old_file.get('subtype', "")
                if old_subtype and old_subtype != subtype:
                    error_message, error_code = Errors.breaking_backwards_subtype()
                    if self.handle_error(error_message, error_message, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        return True

        return False

    def is_valid_subtype(self):
        """Validate that the subtype is python2 or python3."""
        type_ = self.current_file.get('type')
        if type_ == 'python':
            subtype = self.current_file.get('subtype')
            if subtype not in PYTHON_SUBTYPES:
                error_message, error_code = Errors.wrong_subtype()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

    def is_added_required_args(self):
        """Check if required arg were added."""
        current_args_to_required = self._get_arg_to_required_dict(self.current_file)
        old_args_to_required = self._get_arg_to_required_dict(self.old_file)

        for arg, required in current_args_to_required.items():
            if required:
                if (arg not in old_args_to_required) or \
                        (arg in old_args_to_required and required != old_args_to_required[arg]):
                    error_message, error_code = Errors.added_required_fields(arg)
                    if self.handle_error(error_message, error_code, file_path=self.file_path,
                                         warning=self.structure_validator.quite_bc):
                        return True
        return False

    def no_incident_in_core_pack(self):
        """check if args name contains the word incident"""
        args = self.current_file.get('args', [])
        strings_with_incident_list = []
        no_incidents = True
        for arg in args:
            if 'incident' in arg['name']:
                strings_with_incident_list.append(arg['name'])

        if strings_with_incident_list:
            error_message, error_code = Errors.incident_in_script_arg(strings_with_incident_list)
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 suggested_fix=Errors.suggest_server_allowlist_fix()):
                self.is_valid = False
                no_incidents = False

        return no_incidents

    def is_there_duplicates_args(self):
        # type: () -> bool
        """Check if there are duplicated arguments."""
        args = [arg['name'] for arg in self.current_file.get('args', [])]
        if len(args) != len(set(args)) and not self.structure_validator.quite_bc:
            return True
        return False

    def is_arg_changed(self):
        # type: () -> bool
        """Check if the argument has been changed."""
        current_args = [arg['name'] for arg in self.current_file.get('args', [])]
        old_args = [arg['name'] for arg in self.old_file.get('args', [])]

        if not self._is_sub_set(current_args, old_args):
            error_message, error_code = Errors.breaking_backwards_arg_changed()
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 warning=self.structure_validator.quite_bc):
                return True

        return False

    def is_context_path_changed(self):
        # type: () -> bool
        """Check if the context path as been changed."""
        current_context = [output['contextPath'] for output in self.current_file.get('outputs') or []]
        old_context = [output['contextPath'] for output in self.old_file.get('outputs') or []]

        if not self._is_sub_set(current_context, old_context):
            error_message, error_code = Errors.breaking_backwards_context()
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 warning=self.structure_validator.quite_bc):
                return True

        return False

    def is_id_equals_name(self):
        """Check whether the script's ID is equal to its name

            Returns:
                bool. Whether the script's id equals to its name
            """
        return super(ScriptValidator, self)._is_id_equals_name('script')

    def is_docker_image_valid(self):
        # type: () -> bool
        # dockers should not be checked when running on all files
        # dockers should not be checked when running on ApiModules scripts
        if self.skip_docker_check or API_MODULES_PACK in self.file_path:
            return True

        docker_image_validator = DockerImageValidator(self.file_path, is_modified_file=True, is_integration=False,
                                                      ignored_errors=self.ignored_errors,
                                                      print_as_warnings=self.print_as_warnings,
                                                      suppress_print=self.suppress_print,
                                                      json_file_path=self.json_file_path)
        if docker_image_validator.is_docker_image_valid():
            return True
        return False

    def is_valid_name(self):
        # type: () -> bool
        maybe_version_number: Optional[str] = get_file_version_suffix_if_exists(self.current_file)
        if not maybe_version_number:
            return True
        else:
            name = self.current_file.get('name')
            correct_name = f'V{maybe_version_number}'
            if not name.endswith(correct_name):  # type: ignore
                error_message, error_code = Errors.invalid_version_script_name(maybe_version_number)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

            return True

    def is_valid_pwsh(self) -> bool:
        if self.current_file.get("type") == TYPE_PWSH:
            from_version = self.current_file.get("fromversion", "0.0.0")
            if not from_version or server_version_compare("5.5.0", from_version) > 0:
                error_message, error_code = Errors.pwsh_wrong_version(from_version)
                if self.handle_error(error_message, error_code, file_path=self.file_path,
                                     suggested_fix=Errors.suggest_fix(self.file_path, '--from-version', '5.5.0')):
                    return False

        return True

    def is_valid_as_deprecated(self) -> bool:
        is_valid = True
        is_deprecated = self.current_file.get('deprecated', False)
        comment = self.current_file.get('comment', '')
        deprecated_v2_regex = DEPRECATED_REGEXES[0]
        deprecated_no_replace_regex = DEPRECATED_REGEXES[1]
        if is_deprecated:
            if re.search(deprecated_v2_regex, comment) or re.search(deprecated_no_replace_regex, comment):
                pass
            else:
                error_message, error_code = Errors.invalid_deprecated_script()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_valid = False
        return is_valid

    def is_valid_script_file_path(self) -> bool:
        absolute_file_path = self.file_path
        scripts_folder = os.path.basename(os.path.dirname(absolute_file_path))
        script_file = os.path.basename(absolute_file_path)
        script_file, _ = os.path.splitext(script_file)

        if scripts_folder == 'Scripts':
            if not script_file.startswith('script-'):

                error_message, error_code = Errors.is_valid_script_file_path_in_scripts_folder(script_file)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        elif script_file != scripts_folder:
            valid_script_file = script_file.replace('-', '').replace('_', '')

            if valid_script_file.lower() != scripts_folder.lower():
                error_message, error_code = Errors.is_valid_script_file_path_in_folder(script_file)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

    def is_there_separators_in_names(self) -> bool:
        """
        Check if there are separators in the script folder or files.

        Returns:
            true if the folder/files names are valid and there are no separators, and false if not.
        """
        is_unified_script = self.current_file.get('script', '') not in ['-', '']

        if is_unified_script:
            return True

        answers = [
            self.check_separators_in_folder(),
            self.check_separators_in_files()
        ]

        return all(answers)

    def check_separators_in_folder(self) -> bool:
        """
        Check if there are separators in the script folder name.

        Returns:
            true if the name is valid and there are no separators, and false if not.
        """

        script_folder_name = os.path.basename(os.path.dirname(self.file_path))
        valid_folder_name = self.remove_separators_from_name(script_folder_name)

        if valid_folder_name != script_folder_name:
            error_message, error_code = Errors.folder_name_has_separators('script', script_folder_name,
                                                                          valid_folder_name)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def check_separators_in_files(self):
        """
        Check if there are separators in the script files names.

        Returns:
            true if the files names are valid and there is no separators, and false if not.
        """

        # Gets the all script files that may have the script name as base name
        files_to_check = get_files_in_dir(os.path.dirname(self.file_path), ['yml', 'py'], False)
        valid_files = []
        invalid_files = []

        for file_path in files_to_check:

            file_name = os.path.basename(file_path)

            if file_name.endswith('_test.py') or file_name.endswith('_unified.yml'):
                base_name = file_name.rsplit('_', 1)[0]

            else:
                base_name = file_name.rsplit('.', 1)[0]

            valid_base_name = self.remove_separators_from_name(base_name)

            if valid_base_name != base_name:
                valid_files.append(valid_base_name.join(file_name.rsplit(base_name, 1)))
                invalid_files.append(file_name)

        if invalid_files:

            error_message, error_code = Errors.file_name_has_separators('script', invalid_files, valid_files)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def name_not_contain_the_type(self):
        """
        Check that the entity name does not contain the entity type
        Returns: True if the name is valid
        """

        name = self.current_file.get('name', '')
        if 'script' in name.lower():
            error_message, error_code = Errors.field_contain_forbidden_word(field_names=['name'], word='script')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False
        return True

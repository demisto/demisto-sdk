from demisto_sdk.commands.common.constants import PYTHON_SUBTYPES, TYPE_PWSH
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.hook_validations.utils import is_v2_file
from demisto_sdk.commands.common.tools import server_version_compare


class ScriptValidator(ContentEntityValidator):
    """ScriptValidator is designed to validate the correctness of the file structure we enter to content repo. And
        also try to catch possible Backward compatibility breaks due to the preformed changes.
    """

    def is_valid_version(self):
        # type: () -> bool
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
            self.is_changed_subtype(),
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
        ])
        # check only on added files
        if not self.old_file:
            is_script_valid = all([
                is_script_valid,
                self.is_valid_name()
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
                    if self.handle_error(error_message, error_message, file_path=self.file_path):
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
                    if self.handle_error(error_message, error_code, file_path=self.file_path):
                        return True
        return False

    def is_there_duplicates_args(self):
        # type: () -> bool
        """Check if there are duplicated arguments."""
        args = [arg['name'] for arg in self.current_file.get('args', [])]
        if len(args) != len(set(args)):
            return True
        return False

    def is_arg_changed(self):
        # type: () -> bool
        """Check if the argument has been changed."""
        current_args = [arg['name'] for arg in self.current_file.get('args', [])]
        old_args = [arg['name'] for arg in self.old_file.get('args', [])]

        if not self._is_sub_set(current_args, old_args):
            error_message, error_code = Errors.breaking_backwards_arg_changed()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return True

        return False

    def is_context_path_changed(self):
        # type: () -> bool
        """Check if the context path as been changed."""
        current_context = [output['contextPath'] for output in self.current_file.get('outputs', [])]
        old_context = [output['contextPath'] for output in self.old_file.get('outputs', [])]

        if not self._is_sub_set(current_context, old_context):
            error_message, error_code = Errors.breaking_backwards_context()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
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
        # dockers should not be checked on master branch
        if self.branch_name == 'master':
            return True

        docker_image_validator = DockerImageValidator(self.file_path, is_modified_file=True, is_integration=False,
                                                      ignored_errors=self.ignored_errors,
                                                      print_as_warnings=self.print_as_warnings)
        if docker_image_validator.is_docker_image_valid():
            return True
        return False

    def is_valid_name(self):
        # type: () -> bool
        if not is_v2_file(self.current_file):
            return True
        else:
            name = self.current_file.get('name')
            correct_name = "V2"
            if not name.endswith(correct_name):
                error_message, error_code = Errors.invalid_v2_script_name()
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

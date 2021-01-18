import tempfile
from typing import Optional, Union

import click
import demisto_client
from demisto_sdk.commands.common.constants import (API_MODULES_PACK,
                                                   DEFAULT_VERSION,
                                                   FEATURE_BRANCHES,
                                                   OLDEST_SUPPORTED_VERSION,
                                                   PYTHON_SUBTYPES, SCRIPT,
                                                   TYPE_PWSH, FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import \
    Readme
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.docker import \
    DockerImageValidator
from demisto_sdk.commands.common.tools import (get_demisto_version,
                                               get_old_file, is_v2_file)
from packaging.version import Version, parse
from wcmatch.pathlib import Path


class Script(YAMLContentUnifiedObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, FileType.SCRIPT, SCRIPT)
        self.base = base if base else BaseValidator()

    @property
    def readme(self) -> Optional[Readme]:
        return None

    def upload(self, client: demisto_client):
        """
        Upload the integration to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if self.is_unify():
            return client.import_script(file=self.path)
        else:
            with tempfile.TemporaryDirectory() as dir:
                unified_files = self._unify(dir)
                for file in unified_files:
                    if (str(file)[-7:] == '_45.yml') == (get_demisto_version(client) < parse('4.6.0')):
                        # The above condition checks that the file ends in `_45.yml' and the version is 4.5 or less
                        # or that the file doesn't end in `_45.yml` and the version is higher than 4.5
                        return client.import_script(file=file)

    def validate(self):
        old_file = get_old_file(self.path, self.base.old_file_path, self.base.prev_ver, suppress_print=True)

        if self.check_if_integration_is_deprecated():
            click.echo(f"Validating deprecated file: {self.path}")
            valid_deprecated = self.is_valid_as_deprecated()
            if self.base.check_bc:
                return all([valid_deprecated, self.is_backward_compatible(old_file)])
            else:
                return valid_deprecated

        if self.base.file_type == FileType.TEST_SCRIPT:
            return self.is_valid_test_script()

        if self.base.check_bc:
            return self.is_valid_file(old_file) and self.is_backward_compatible(old_file)
        else:
            return self.is_valid_file(old_file)

    def is_valid_test_script(self):
        return all([
            self.is_valid_version(),
            self.is_valid_fromversion()
        ])

    def is_backward_compatible(self, old_file):
        # type: (dict) -> bool
        """Check if the script is backward compatible."""
        if not old_file:
            return True

        is_breaking_backwards = [
            self.is_context_path_changed(old_file),
            self.is_added_required_args(old_file),
            self.is_arg_changed(old_file),
            self.is_changed_subtype(old_file)
        ]

        # Add sane-doc-report exception
        # Sane-doc-report uses docker and every fix/change requires a docker tag change,
        # thus it won't be backwards compatible.
        # All other tests should be False (i.e. no problems)
        if self.path == 'Scripts/SaneDocReport/SaneDocReport.yml':
            return not any(is_breaking_backwards[1:])
        return not any(is_breaking_backwards)

    def is_valid_file(self, old_file):
        # type: (dict) -> bool
        """Check whether the script is valid or not"""
        is_script_valid = all([
            self.is_valid_version(),
            self.is_valid_fromversion(),
            self.is_valid_subtype(),
            self.is_id_equals_name(),
            self.is_docker_image_valid(),
            self.is_valid_pwsh(),
            self.no_duplicates_args()
        ])
        # check only on added files
        if not old_file:
            is_script_valid = all([
                is_script_valid,
                self.is_valid_name()
            ])
        return is_script_valid

    def check_if_integration_is_deprecated(self):
        is_deprecated = self.get('deprecated', False)

        toversion_is_old = self.to_version < Version(OLDEST_SUPPORTED_VERSION)

        return is_deprecated or toversion_is_old

    def is_valid_as_deprecated(self) -> bool:
        is_valid = True
        comment = self.get('comment', '')
        if self.get('deprecated', False) and not comment.startswith('Deprecated.'):
            error_message, error_code = Errors.invalid_deprecated_script()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False
        return is_valid

    def is_valid_subtype(self):
        """Validate that the subtype is python2 or python3."""
        type_ = self.get('type')
        if type_ == 'python':
            subtype = self.get('subtype')
            if subtype not in PYTHON_SUBTYPES:
                error_message, error_code = Errors.wrong_subtype()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

        return True

    def is_id_equals_name(self):
        """Validate that the id of the file equals to the name.
        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = self.get('commonfields', {}).get('id')
        name = self.get('name', '')
        if file_id != name:
            error_message, error_code = Errors.id_should_equal_name(name, file_id)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False

        return True

    def is_docker_image_valid(self):
        # type: () -> bool
        # dockers should not be checked when running on all files
        # dockers should not be checked when running on ApiModules scripts
        if self.base.skip_docker_check or API_MODULES_PACK in str(self.path):
            return True

        docker_image_validator = DockerImageValidator(str(self.path), is_modified_file=True, is_integration=False,
                                                      ignored_errors=self.base.ignored_errors,
                                                      print_as_warnings=self.base.print_as_warnings,
                                                      suppress_print=self.base.suppress_print)
        if docker_image_validator.is_docker_image_valid():
            return True
        return False

    def is_valid_pwsh(self) -> bool:
        if self.get("type") == TYPE_PWSH:
            from_version = self.get("fromversion")
            if not from_version or self.from_version < Version('5.5.0'):
                error_message, error_code = Errors.pwsh_wrong_version(from_version)
                if self.base.handle_error(error_message, error_code, file_path=self.path,
                                          suggested_fix=Errors.suggest_fix(self.path, '--from-version', '5.5.0')):
                    return False

        return True

    def is_valid_name(self):
        # type: () -> bool
        if not is_v2_file(self):
            return True
        else:
            name = self.get('name')
            correct_name = "V2"
            if not name.endswith(correct_name):  # type: ignore
                error_message, error_code = Errors.invalid_v2_script_name()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False

            return True

    def is_valid_version(self):
        # type: () -> bool
        if self.get('commonfields', {}).get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.base.prev_ver or feature_branch_name in self.base.branch_name)
               for feature_branch_name in FEATURE_BRANCHES):
            return False

        return True

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromversion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
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

    def is_context_path_changed(self, old_file):
        # type: (dict) -> bool
        """Check if the context path as been changed."""
        current_context = [output['contextPath'] for output in self.get('outputs', [])]
        old_context = [output['contextPath'] for output in old_file.get('outputs', [])]

        if not self._is_sub_set(current_context, old_context):
            error_message, error_code = Errors.breaking_backwards_context()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return True

        return False

    def _get_arg_to_required_dict(self, script_json: dict = None):
        """Get a dictionary arg name to its required status.

        Args:
            script_json (dict): Dictionary of the examined script.

        Returns:
            dict. arg name to its required status.
        """
        arg_to_required = {}
        if script_json:
            args = script_json.get('args', [])
        else:
            args = self.get('args', [])
        for arg in args:
            arg_to_required[arg.get('name')] = arg.get('required', False)
        return arg_to_required

    def is_added_required_args(self, old_file):
        """Check if required arg were added."""
        current_args_to_required = self._get_arg_to_required_dict()
        old_args_to_required = self._get_arg_to_required_dict(old_file)

        for arg, required in current_args_to_required.items():
            if required:
                if (arg not in old_args_to_required) or \
                        (arg in old_args_to_required and required != old_args_to_required[arg]):
                    error_message, error_code = Errors.added_required_fields(arg)
                    if self.base.handle_error(error_message, error_code, file_path=self.path):
                        return True
        return False

    def is_arg_changed(self, old_file):
        # type: (dict) -> bool
        """Check if the argument has been changed."""
        current_args = [arg['name'] for arg in self.get('args', [])]
        old_args = [arg['name'] for arg in old_file.get('args', [])]

        if not self._is_sub_set(current_args, old_args):
            error_message, error_code = Errors.breaking_backwards_arg_changed()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return True

        return False

    def no_duplicates_args(self):
        # type: () -> bool
        """Check if there are duplicated arguments."""
        is_valid = True
        args = [arg['name'] for arg in self.get('args', [])]
        for arg in args:
            if args.count(arg) > 1:
                error_message, error_code = Errors.duplicated_argument_in_script(arg)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_valid = False

        return is_valid

    def is_changed_subtype(self, old_file):
        """Validate that the subtype was not changed."""
        type_ = self.get('type')
        if type_ == 'python':
            subtype = self.get('subtype')
            if old_file:
                old_subtype = old_file.get('subtype', "")
                if old_subtype and old_subtype != subtype:
                    error_message, error_code = Errors.breaking_backwards_subtype()
                    if self.base.handle_error(error_message, error_message, file_path=self.path):
                        return True

        return False

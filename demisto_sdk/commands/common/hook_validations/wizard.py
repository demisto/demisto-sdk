import click

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION, WIZARD, FileType)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class WizardValidator(ContentEntityValidator):

    def __init__(self, structure_validator, ignored_errors=False, print_as_warnings=False, json_file_path=None,
                 **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, json_file_path=json_file_path,
                         oldest_supported_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.WIZARD),
                         **kwargs)
        self._errors = []

    def get_errors(self):
        return "\n".join(self._errors)

    def are_dependency_packs_valid(self, id_set_file):
        if not id_set_file:
            click.secho("Skipping wizard pack validation. Could not read id_set.json.", fg="yellow")
            return True

        deps_are_valid = True
        wizard_dependencies = set()
        for pack_metadata in self.current_file.get("dependency_packs", []):
            packs = [pack.get('name', '') for pack in pack_metadata.get("packs", [])]
            wizard_dependencies.update(packs)
        packs = id_set_file.get('Packs', {})
        for dep in wizard_dependencies:
            if dep not in packs:
                error_message, error_code = Errors.invalid_dependency_pack_in_wizard(dep)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    deps_are_valid = False
        return deps_are_valid

    def is_valid_version(self):
        # not validated
        return True

    def is_valid_file(self, validate_rn=True, id_set_file=None):
        return all((
            self._is_id_equals_name(WIZARD),
            self.are_dependency_packs_valid(id_set_file),
            super().is_valid_file(validate_rn),
        ))

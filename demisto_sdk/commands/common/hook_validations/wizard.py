from typing import Optional

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    WIZARD,
    FileType,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_pack_name


class WizardValidator(ContentEntityValidator):
    def __init__(
        self,
        structure_validator,
        ignored_errors=False,
        json_file_path=None,
        **kwargs,
    ):
        super().__init__(
            structure_validator,
            ignored_errors,
            json_file_path=json_file_path,
            oldest_supported_version=FILETYPE_TO_DEFAULT_FROMVERSION.get(
                FileType.WIZARD
            ),
            **kwargs,
        )
        self._errors = []

        self._pack_deps = self.collect_packs_dependencies()
        # add self pointing pack in case of internal content usage
        self._pack_deps.add(get_pack_name(self.file_path))
        self._fetching_integrations = self.collect_integrations(
            integration_category="fetching_integrations"
        )
        self._supporting_integrations = self.collect_integrations(
            integration_category="supporting_integrations"
        )
        self._set_playbooks = self.collect_set_playbooks()

    def collect_packs_dependencies(self) -> set:
        wizard_dependencies = set()
        for pack_metadata in self.current_file.get("dependency_packs", []):
            packs = [pack.get("name", "") for pack in pack_metadata.get("packs", [])]
            wizard_dependencies.update(packs)
        return wizard_dependencies

    def collect_set_playbooks(self) -> dict:
        set_playbooks = self.current_file.get("wizard", {}).get("set_playbook", [])
        return {
            playbook.get("name", ""): playbook.get("link_to_integration")
            for playbook in set_playbooks
        }

    def collect_integrations(self, integration_category: str) -> set:
        integrations = self.current_file.get("wizard", {}).get(integration_category, [])
        return {integration.get("name", "") for integration in integrations}

    @error_codes("WZ100")
    def are_dependency_packs_valid(self, id_set_file: Optional[dict]):
        if not id_set_file:
            logger.info(
                "<yellow>Skipping wizard dependency pack validation. Could not read id_set.json.</yellow>"
            )
            return True

        deps_are_valid = True
        packs = id_set_file.get("Packs", {})
        for dep in self._pack_deps:
            if dep not in packs:
                error_message, error_code = Errors.invalid_dependency_pack_in_wizard(
                    dep
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    deps_are_valid = False
        return deps_are_valid

    @error_codes("WZ101,WZ102")
    def are_integrations_in_dependency_packs(self, id_set_file: Optional[dict]):
        if not id_set_file:
            logger.info(
                "<yellow>Skipping wizard integrations validation. Could not read id_set.json.</yellow>"
            )
            return True

        def are_integrations_mapped_to_dependency_packs(integrations: set) -> bool:
            integration_in_dependency_packs = True
            for integration in integrations:
                if integration not in integrations_to_pack:
                    error_message, error_code = Errors.invalid_integration_in_wizard(
                        integration
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        integration_in_dependency_packs = False
                elif (pack := integrations_to_pack[integration]) not in self._pack_deps:
                    (
                        error_message,
                        error_code,
                    ) = Errors.missing_dependency_pack_in_wizard(
                        pack, f'integration "{integration}"'
                    )
                    if self.handle_error(
                        error_message, error_code, file_path=self.file_path
                    ):
                        integration_in_dependency_packs = False

            return integration_in_dependency_packs

        integrations_to_pack = {
            list(integration.keys())[0]: list(integration.values())[0]["pack"]
            for integration in id_set_file["integrations"]
        }

        return all(
            (
                are_integrations_mapped_to_dependency_packs(
                    self._fetching_integrations
                ),
                are_integrations_mapped_to_dependency_packs(
                    self._supporting_integrations
                ),
            )
        )

    @error_codes("WZ101,WZ103")
    def are_playbooks_in_dependency_packs(self, id_set_file: Optional[dict]):
        if not id_set_file:
            logger.info(
                "<yellow>Skipping wizard playbooks validation. Could not read id_set.json.</yellow>"
            )
            return True

        playbooks_to_pack = {
            list(playbook.keys())[0]: list(playbook.values())[0]["pack"]
            for playbook in id_set_file["playbooks"]
        }

        playbooks_in_dependency_packs = True
        for playbook in self._set_playbooks:
            if playbook not in playbooks_to_pack:
                error_message, error_code = Errors.invalid_playbook_in_wizard(playbook)
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    playbooks_in_dependency_packs = False
            elif (pack := playbooks_to_pack[playbook]) not in self._pack_deps:
                error_message, error_code = Errors.missing_dependency_pack_in_wizard(
                    pack, f'playbook "{playbook}"'
                )
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    playbooks_in_dependency_packs = False

        return playbooks_in_dependency_packs

    @error_codes("WZ104,WZ105")
    def do_all_fetch_integrations_have_playbook(self):
        all_fetch_integrations_have_playbook = True
        integrations = self._fetching_integrations.copy()
        for link in self._set_playbooks.values():
            if not link:  # handle case that a playbook was mapped to all integration
                return True
            if link not in integrations:
                error_message, error_code = Errors.wrong_link_in_wizard(link)
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    all_fetch_integrations_have_playbook = False
            else:
                integrations.remove(link)
        if len(integrations) != 0:
            error_message, error_code = Errors.wizard_integrations_without_playbooks(
                integrations
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                all_fetch_integrations_have_playbook = False
        return all_fetch_integrations_have_playbook

    def is_valid_version(self):
        # not validated
        return True

    def is_valid_file(self, validate_rn=True, id_set_file=None):
        return all(
            (
                self._is_id_equals_name(WIZARD),
                self.are_integrations_in_dependency_packs(id_set_file),
                self.are_playbooks_in_dependency_packs(id_set_file),
                self.are_dependency_packs_valid(id_set_file),
                self.do_all_fetch_integrations_have_playbook(),
                super().is_valid_file(validate_rn),
            )
        )

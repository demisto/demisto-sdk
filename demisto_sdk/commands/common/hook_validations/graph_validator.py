from collections import defaultdict
from typing import List, Optional

from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import (
    get_all_content_objects_paths_in_dir,
    get_marketplace_to_core_packs,
    get_pack_name,
    replace_incident_to_alert,
)
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GraphValidator(BaseValidator):
    """GraphValidator makes validations on the content graph."""

    def __init__(
        self,
        specific_validations: list = None,
        git_files: list = None,
        input_files: list = None,
        update_graph: bool = True,
        include_optional_deps: bool = False,
    ):
        super().__init__(specific_validations=specific_validations)
        self.include_optional = include_optional_deps
        self.graph = ContentGraphInterface()
        if update_graph:
            update_content_graph(
                self.graph,
                use_git=True,
                output_path=self.graph.output_path,
            )
        self.file_paths: List[str] = git_files or get_all_content_objects_paths_in_dir(
            input_files
        )
        self.pack_ids: List[str] = []
        for file_path in self.file_paths:
            pack_name: Optional[str] = get_pack_name(file_path)
            if pack_name and pack_name not in self.pack_ids:
                self.pack_ids.append(pack_name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.graph.__exit__()

    def is_valid_content_graph(self) -> bool:
        is_valid = (
            self.validate_hidden_packs_do_not_have_mandatory_dependencies(),
            self.validate_dependencies(),
            self.validate_marketplaces_fields(),
            self.validate_fromversion_fields(),
            self.validate_toversion_fields(),
            self.is_file_display_name_already_exists(),
            self.validate_duplicate_ids(),
            self.validate_unique_script_name(),
        )
        return all(is_valid)

    def validate_dependencies(self):
        """Validating the pack dependencies"""
        is_valid = []
        is_valid.append(self.are_core_pack_dependencies_valid())
        return all(is_valid)

    @error_codes("GR105")
    def validate_duplicate_ids(self):
        is_valid = True
        for content_item, duplicates in self.graph.validate_duplicate_ids(
            self.file_paths
        ):
            for duplicate in duplicates:
                error_message, error_code = Errors.duplicated_id(
                    content_item.object_id, duplicate.path
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path=content_item.path,
                    drop_line=True,
                ):
                    is_valid = False
        return is_valid

    @error_codes("PA124")
    def are_core_pack_dependencies_valid(self):
        """Validates, for each marketplace version, that its core packs don't depend on non-core packs.
        On `validate -a`, all core packs are checked.

        Note: if at the first-level dependency of core packs there are only core packs, for every
            core pack, then it is true for all levels. Thus, checking only the first level of
            DEPENDS_ON relationships suffices for this validation.
        """
        is_valid = True

        mp_to_core_packs = get_marketplace_to_core_packs()
        for marketplace, mp_core_packs in mp_to_core_packs.items():
            if not self.pack_ids:
                pack_ids_to_check = list(mp_core_packs)
            else:
                pack_ids_to_check = [
                    pack_id for pack_id in self.pack_ids if pack_id in mp_core_packs
                ]

            for core_pack_node in self.graph.find_core_packs_depend_on_non_core_packs(
                pack_ids_to_check, marketplace, list(mp_core_packs)
            ):
                non_core_pack_dependencies = [
                    relationship.content_item_to.object_id
                    for relationship in core_pack_node.depends_on
                    if not relationship.is_test
                ]
                error_message, error_code = Errors.invalid_core_pack_dependencies(
                    core_pack_node.object_id, non_core_pack_dependencies
                )
                if self.handle_error(
                    error_message, error_code, file_path=core_pack_node.path
                ):
                    is_valid = False

        return is_valid

    @error_codes("GR100")
    def validate_marketplaces_fields(self):
        """
        Source's marketplaces field is a subset of the target's marketplaces field
        """
        is_valid = True
        content_item: ContentItem
        for content_item in self.graph.find_uses_paths_with_invalid_marketplaces(
            self.pack_ids
        ):
            used_content_items = [
                relationship.content_item_to.object_id
                for relationship in content_item.uses
            ]
            error_message, error_code = Errors.uses_items_not_in_marketplaces(
                content_item.name, content_item.marketplaces, used_content_items
            )
            if self.handle_error(error_message, error_code, content_item.path):
                is_valid = False

        return is_valid

    @error_codes("GR101")
    def validate_fromversion_fields(self):
        """Validates that source's fromversion >= target's fromversion."""
        is_valid = []

        # Returns warnings - for non supported versions
        content_items_with_invalid_fromversion: List[ContentItem] = (
            self.graph.find_uses_paths_with_invalid_fromversion(
                self.file_paths, for_supported_versions=False
            )
        )
        for content_item in content_items_with_invalid_fromversion:
            is_valid.append(self.handle_invalid_fromversion(content_item, warning=True))

        # Returns errors - for supported versions
        content_items_with_invalid_fromversion = (
            self.graph.find_uses_paths_with_invalid_fromversion(
                self.file_paths, for_supported_versions=True
            )
        )
        for content_item in content_items_with_invalid_fromversion:
            is_valid.append(self.handle_invalid_fromversion(content_item))

        return all(is_valid)

    def handle_invalid_fromversion(
        self, content_item: ContentItem, warning: bool = False
    ):
        is_valid = True
        """Handles a single invalid fromversion query result"""
        used_content_items = [
            relationship.content_item_to.object_id for relationship in content_item.uses
        ]
        error_message, error_code = Errors.uses_items_with_invalid_fromversion(
            content_item.name, content_item.fromversion, used_content_items
        )
        if self.handle_error(
            error_message, error_code, content_item.path, warning=warning
        ):
            is_valid = False

        return is_valid

    @error_codes("GR102")
    def validate_toversion_fields(self):
        """Validate that source's toversion <= target's toversion."""
        is_valid = []

        # Returns warnings - for non supported versions
        content_items_with_invalid_versions: List[ContentItem] = (
            self.graph.find_uses_paths_with_invalid_toversion(
                self.file_paths, for_supported_versions=False
            )
        )

        for content_item in content_items_with_invalid_versions:
            is_valid.append(self.handle_invalid_toversion(content_item, warning=True))

        # Returns errors - for supported versions
        content_items_with_invalid_versions = (
            self.graph.find_uses_paths_with_invalid_toversion(
                self.file_paths, for_supported_versions=True
            )
        )
        for content_item in content_items_with_invalid_versions:
            is_valid.append(self.handle_invalid_toversion(content_item))

        return all(is_valid)

    def handle_invalid_toversion(
        self, content_item: ContentItem, warning: bool = False
    ):
        """Handles a single invalid toversion query result"""
        is_valid = True
        used_content_items = [
            relationship.content_item_to.object_id for relationship in content_item.uses
        ]
        error_message, error_code = Errors.uses_items_with_invalid_toversion(
            content_item.name, content_item.toversion, used_content_items
        )
        if self.handle_error(
            error_message, error_code, content_item.path, warning=warning
        ):
            is_valid = False

        return is_valid

    @error_codes("GR104")
    def is_file_display_name_already_exists(self):
        """
        Validate that there are no duplicate display names in the repo
        """
        is_valid = True
        query_results = self.graph.get_duplicate_pack_display_name(self.file_paths)

        if query_results:
            for content_id, duplicate_names_id in query_results:
                (
                    error_message,
                    error_code,
                ) = Errors.multiple_packs_with_same_display_name(
                    content_id, duplicate_names_id
                )
                if self.handle_error(error_message, error_code, ""):
                    is_valid = False

        return is_valid

    @error_codes("GR106")
    def validate_unique_script_name(self):
        """
        Validate that there are no duplicate names of scripts
        when the script name included `alert`.
        """
        is_valid = True
        query_results = self.graph.get_duplicate_script_name_included_incident(
            self.file_paths
        )

        if query_results:
            for script_name, file_path in query_results.items():
                (
                    error_message,
                    error_code,
                ) = Errors.duplicated_script_name(
                    replace_incident_to_alert(script_name), script_name
                )
                if self.handle_error(
                    error_message,
                    error_code,
                    file_path,
                ):
                    is_valid = False

        return is_valid

    @error_codes("GR108")
    def validate_hidden_packs_do_not_have_mandatory_dependencies(self):
        """
        Validate that hidden pack(s) do not have dependant packs which the
        hidden pack is a mandatory dependency for them.
        """
        is_valid = True

        if dependant_packs := self.graph.find_packs_with_invalid_dependencies(
            pack_ids=self.pack_ids
        ):
            hidden_pack_id_to_dependant_pack_ids: dict = defaultdict(set)

            for pack in dependant_packs:
                for relationship in pack.depends_on:
                    hidden_pack_id = relationship.content_item_to.object_id
                    hidden_pack_id_to_dependant_pack_ids[hidden_pack_id].add(
                        pack.object_id
                    )

            for pack_id in hidden_pack_id_to_dependant_pack_ids:
                if dependant_packs_ids := hidden_pack_id_to_dependant_pack_ids.get(
                    pack_id
                ):
                    (
                        error_message,
                        error_code,
                    ) = Errors.hidden_pack_not_mandatory_dependency(
                        hidden_pack=pack_id, dependant_packs_ids=dependant_packs_ids
                    )
                    if self.handle_error(
                        error_message=error_message,
                        error_code=error_code,
                        file_path=f"{PACKS_DIR}/{pack_id}",
                    ):
                        is_valid = False

        return is_valid

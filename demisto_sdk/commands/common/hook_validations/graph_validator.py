from typing import List

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import (
    get_all_content_objects_paths_in_dir,
    get_core_pack_list,
    get_pack_name,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem


class GraphValidator(BaseValidator):
    """GraphValidator makes validations on the content graph."""

    def __init__(
        self,
        specific_validations: list = None,
        git_files: list = None,
        input_files: list = None,
        should_update: bool = True,
    ):
        super().__init__(specific_validations=specific_validations)
        self.graph = ContentGraphInterface(should_update=should_update)
        self.file_paths: List[str] = git_files or get_all_content_objects_paths_in_dir(
            input_files
        )
        self.pack_ids: List[str] = list(
            {get_pack_name(file_path) for file_path in self.file_paths}
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.graph.__exit__()

    def is_valid_content_graph(self) -> bool:
        is_valid = (
            self.validate_dependencies(),
            self.validate_marketplaces_fields(),
            self.validate_fromversion_fields(),
            self.validate_toversion_fields(),
            self.is_file_using_unknown_content(),
            self.is_file_display_name_already_exists(),
        )
        return all(is_valid)

    def validate_dependencies(self):
        """Validating the pack dependencies"""
        is_valid = []
        is_valid.append(self.are_core_pack_dependencies_valid())
        return all(is_valid)

    @error_codes("PA124")
    def are_core_pack_dependencies_valid(self):
        """Validates that core packs don't depend on non-core packs.
        On `validate -a`, all core packs are checked.

        Note: if at the first-level dependency of core packs there are only core packs, for every
            core pack, then it is true for all levels. Thus, checking only the first level of
            DEPENDS_ON relationships suffices for this validation.
        """
        is_valid = True

        core_pack_list = get_core_pack_list()
        if not self.pack_ids:
            pack_ids_to_check = core_pack_list
        else:
            pack_ids_to_check = [
                pack_id for pack_id in self.pack_ids if pack_id in core_pack_list
            ]

        for core_pack_node in self.graph.find_core_packs_depend_on_non_core_packs(
            pack_ids_to_check, core_pack_list
        ):
            non_core_pack_dependencies = [
                relationship.content_item_to.object_id
                for relationship in core_pack_node.depends_on
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
            self.file_paths
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
        content_items_with_invalid_fromversion: List[
            ContentItem
        ] = self.graph.find_uses_paths_with_invalid_fromversion(
            self.file_paths, for_supported_versions=False
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
        content_items_with_invalid_versions: List[
            ContentItem
        ] = self.graph.find_uses_paths_with_invalid_toversion(
            self.file_paths, for_supported_versions=False
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

    @error_codes("GR103")
    def is_file_using_unknown_content(self):
        """Validates that there is no usage of unknown content items."""

        is_valid = True
        content_item: ContentItem
        for content_item in self.graph.get_unknown_content_uses(self.file_paths):
            unknown_content_names = [
                relationship.content_item_to.object_id or relationship.content_item_to.name  # type: ignore
                for relationship in content_item.uses
            ]
            error_message, error_code = Errors.using_unknown_content(
                content_item.name, unknown_content_names
            )
            if self.handle_error(
                error_message, error_code, content_item.path, warning=True
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

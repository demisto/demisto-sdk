from typing import List

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import (
    get_all_content_objects_paths_in_dir,
    get_core_pack_list,
    get_pack_paths_from_files,
)
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import (
    Neo4jContentGraphInterface as ContentGraphInterface,
)


class GraphValidator(BaseValidator):
    """GraphValidator makes validations on the content graph.

    Attributes:
        _is_valid (bool): Whether the conf.json file current state is valid or not.
        conf_data (dict): The data from the conf.json file in our repo.
    """

    def __init__(
        self, specific_validations=None, file_paths=None, validate_specific_files=False
    ):
        super().__init__(self, specific_validations=specific_validations)
        self.graph = ContentGraphInterface(should_update=True)
        self.ignored_errors = {}
        self.file_paths = self.handle_file_paths(file_paths, validate_specific_files)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.graph.__exit__()

    def handle_file_paths(self, file_paths: List[str], validate_specific_files: bool):
        """Transform all of the relevant files to graph format"""
        if file_paths and validate_specific_files:
            all_files = get_all_content_objects_paths_in_dir(file_paths)
            all_files.extend(get_pack_paths_from_files(all_files))
            return all_files
        elif file_paths:
            return file_paths
        else:
            return []

    def is_valid_content_graph(self) -> bool:
        is_valid = (
            self.are_marketplaces_relationships_paths_valid(),
            self.are_fromversion_relationships_paths_valid(),
            self.are_toversion_relationships_paths_valid(),
            self.is_file_using_unknown_content(),
            self.is_file_display_name_already_exists(),
        )
        return all(is_valid)

    def validate_dependencies(self, pack_name):
        """Validating the pack dependencies"""
        is_valid = []

        core_pack_list = get_core_pack_list()
        if pack_name in core_pack_list:
            is_valid.append(
                self.are_core_pack_dependencies_valid(pack_name, core_pack_list)
            )

        return all(is_valid)

    @error_codes("PA124")
    def are_core_pack_dependencies_valid(self, pack_name, core_pack_list):
        """Validating that the core pack does not have dependencieis on non-core packs"""
        is_valid = True
        pack_node = self.graph.search(object_id=pack_name)[0]

        invalid_core_pack_dependencies = [
            dependency.target.object_id
            for dependency in pack_node.depends_on
            if dependency.target.object_id not in core_pack_list
        ]

        if invalid_core_pack_dependencies:
            error_message, error_code = Errors.invalid_core_pack_dependencies(
                pack_name, str(invalid_core_pack_dependencies)
            )
            if self.handle_error(error_message, error_code, file_path=pack_node.path):
                is_valid = False
        return is_valid

    @error_codes("GR101")
    def are_fromversion_relationships_paths_valid(self, file_paths=None):
        """Validate that source's fromvesion >= target's fromvesion."""

        is_valid = []

        # validating content items with minimal from_version: 5.0.0 and maximal from_version 6.4.0
        paths_with_invalid_versions = (
            self.graph.find_uses_paths_with_invalid_fromversion(file_paths)
        )

        for query_result in paths_with_invalid_versions:
            is_valid.append(self.handle_invalid_fromversion(query_result, warning=True))

        # validating content items with at least from_version: 6.5.0
        paths_with_invalid_versions = (
            self.graph.find_uses_paths_with_invalid_fromversion(
                file_paths, from_version=True
            )
        )
        for query_result in paths_with_invalid_versions:
            is_valid.append(self.handle_invalid_fromversion(query_result))

        return all(is_valid)

    def handle_invalid_fromversion(self, query_result, warning=False):
        """Handle the invalid from_version query results"""

        is_valid = True
        content_name = query_result.name
        relationship_data = query_result.uses
        fromversion = query_result.fromversion
        content_items = [
            relationship.target.object_id for relationship in relationship_data
        ]
        file_path = query_result.path
        error_message, error_code = Errors.uses_items_with_invalid_fromversions(
            content_name, fromversion, content_items
        )
        if self.handle_error(error_message, error_code, file_path, warning=warning):
            is_valid = False

        return is_valid

    @error_codes("GR104")
    def are_toversion_relationships_paths_valid(self, file_paths=None):
        """Validate that source's toversion <= target's toversion."""
        is_valid = []
        # validating content items with minimal to_version: 5.0.0 and maximal to_version 6.4.0
        paths_with_invalid_versions = self.graph.find_uses_paths_with_invalid_toversion(
            file_paths
        )

        for query_result in paths_with_invalid_versions:
            is_valid.append(self.handle_invalid_toversion(query_result, warning=True))

        # validating content items with at least to_version: 6.5.0
        paths_with_invalid_versions = self.graph.find_uses_paths_with_invalid_toversion(
            file_paths, to_version=True
        )
        for query_result in paths_with_invalid_versions:
            is_valid.append(self.handle_invalid_toversion(query_result))

        return all(is_valid)

    def handle_invalid_toversion(self, query_result, warning=False):
        """Handle the invalid to_version query results"""

        is_valid = True
        content_name = query_result.name
        relationship_data = query_result.uses
        toversion = query_result.toversion
        content_items = [
            relationship.target.object_id for relationship in relationship_data
        ]
        file_path = query_result.path
        error_message, error_code = Errors.uses_items_with_invalid_toversions(
            content_name, toversion, content_items
        )
        if self.handle_error(error_message, error_code, file_path, warning=warning):
            is_valid = False

        return is_valid

    @error_codes("GR100")
    def are_marketplaces_relationships_paths_valid(self):
        """
        Source's marketplaces field is a subset of the target's marketplaces field
        """

        is_valid = True
        paths_with_invalid_marketplaces = (
            self.graph.find_uses_paths_with_invalid_marketplaces(self.file_paths)
        )

        for query_result in paths_with_invalid_marketplaces:
            content_name = query_result.name
            relationship_data = query_result.uses
            marketplaces = query_result.marketplaces
            content_items = [
                relationship.target.name
                if relationship.target.name
                else relationship.target.object_id
                for relationship in relationship_data
            ]
            file_path = query_result.path
            error_message, error_code = Errors.uses_items_not_in_marketplaces(
                content_name, marketplaces, content_items
            )
            if self.handle_error(error_message, error_code, file_path, warning=True):
                is_valid = False

        return is_valid

    @error_codes("GR102")
    def is_file_using_unknown_content(self):
        """
        Validate that there are no usage of unknown content items
        """

        is_valid = True
        query_results = self.graph.get_unknown_content_uses(self.file_paths)
        if query_results:
            for query_result in query_results:
                content_name = query_result.name
                relationship_data = query_result.uses
                unknown_content_names = [
                    relationship.target.identifier for relationship in relationship_data
                ]
                file_path = query_result.path
                error_message, error_code = Errors.using_unknown_content(
                    content_name, unknown_content_names
                )
                if self.handle_error(
                    error_message, error_code, file_path, warning=True
                ):
                    is_valid = False

        return is_valid

    @error_codes("GR103")
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

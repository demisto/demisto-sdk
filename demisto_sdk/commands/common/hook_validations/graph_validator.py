from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import (
    BaseValidator,
    error_codes,
)
from demisto_sdk.commands.common.tools import (
    get_pack_display_name_from_file_in_pack,
    get_pack_name,
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

    def __init__(self, specific_validations=None):
        super().__init__(self, specific_validations=specific_validations)
        self.graph = ContentGraphInterface()
        self.ignored_errors = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.graph.__exit__()

    def is_valid_files(self, file_paths=[]) -> bool:
        is_valid = (
            self.are_marketplaces_relationships_paths_valid(file_paths),
            self.are_fromversion_relationships_paths_valid(file_paths),
            self.are_toversion_relationships_paths_valid(file_paths),
            self.is_file_using_unknown_content(file_paths),
            self.is_file_display_name_already_exists(file_paths),
        )
        return all(is_valid)

    @error_codes("GR101")
    def are_fromversion_relationships_paths_valid(self, file_paths=None):
        """Validate that source's fromvesion >= target's fromvesion."""

        is_valid = []

        # validating content items with minimal from_version: 5.0.0
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
        from demisto_sdk.commands.validate.validate_manager import ValidateManager

        is_valid = True
        content_name = query_result.name
        relationship_data = query_result.uses
        fromversion = query_result.fromversion
        content_items = [
            relationship.target.name
            if relationship.target.name
            else relationship.target.object_id
            for relationship in relationship_data
        ]
        file_path = query_result.path
        self.ignored_errors = ValidateManager.get_error_ignore_list(
            get_pack_name(file_path)
        )
        error_message, error_code = Errors.uses_with_invalid_fromversions(
            content_name, fromversion, content_items
        )
        if self.handle_error(error_message, error_code, file_path, warning=warning):
            is_valid = False

        return is_valid

    @error_codes("GR104")
    def are_toversion_relationships_paths_valid(self, file_paths=None):
        """Validate that source's toversion <= target's toversion."""
        is_valid = []
        # validating content items with minimal from_version: 5.0.0
        paths_with_invalid_versions = self.graph.find_uses_paths_with_invalid_toversion(
            file_paths
        )

        for query_result in paths_with_invalid_versions:
            is_valid.append(self.handle_invalid_toversion(query_result, warning=True))

        # validating content items with at least from_version: 6.5.0
        paths_with_invalid_versions = self.graph.find_uses_paths_with_invalid_toversion(
            file_paths, to_version=True
        )
        for query_result in paths_with_invalid_versions:
            is_valid.append(self.handle_invalid_toversion(query_result))

        return all(is_valid)

    def handle_invalid_toversion(self, query_result, warning=False):
        """Handle the invalid to_version query results"""
        from demisto_sdk.commands.validate.validate_manager import ValidateManager

        is_valid = True
        content_name = query_result.name
        relationship_data = query_result.uses
        toversion = query_result.toversion
        content_items = [
            relationship.target.name
            if relationship.target.name
            else relationship.target.object_id
            for relationship in relationship_data
        ]
        file_path = query_result.path
        self.ignored_errors = ValidateManager.get_error_ignore_list(
            get_pack_name(file_path)
        )
        error_message, error_code = Errors.uses_with_invalid_toversions(
            content_name, toversion, content_items
        )
        if self.handle_error(error_message, error_code, file_path, warning=warning):
            is_valid = False

        return is_valid

    @error_codes("GR100")
    def are_marketplaces_relationships_paths_valid(self, file_paths=None):
        """
        Source's marketplaces field is a subset of the target's marketplaces field
        """
        from demisto_sdk.commands.validate.validate_manager import ValidateManager

        is_valid = True
        paths_with_invalid_marketplaces = (
            self.graph.find_uses_paths_with_invalid_marketplaces(file_paths)
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
            self.ignored_errors = ValidateManager.get_error_ignore_list(
                get_pack_name(file_path)
            )
            error_message, error_code = Errors.uses_with_invalid_marketplaces(
                content_name, marketplaces, content_items
            )
            if self.handle_error(error_message, error_code, file_path, warning=True):
                is_valid = False

        return is_valid

    @error_codes("GR102")
    def is_file_using_unknown_content(self, file_paths=[]):
        """
        Validate that there are no usage of unknown content items
        """
        from demisto_sdk.commands.validate.validate_manager import ValidateManager

        is_valid = True
        query_results = self.graph.get_unknown_content_uses(file_paths)

        if query_results:
            for query_result in query_results:
                content_name = query_result.name
                relationship_data = query_result.uses
                unknown_content_names = [
                    relationship.target.identifier for relationship in relationship_data
                ]
                file_path = query_result.path
                self.ignored_errors = ValidateManager.get_error_ignore_list(
                    get_pack_name(file_path)
                )
                error_message, error_code = Errors.using_unknown_content(
                    content_name, unknown_content_names
                )
                if self.handle_error(
                    error_message, error_code, file_path, warning=True
                ):
                    is_valid = False

        return is_valid

    @error_codes("GR103")
    def is_file_display_name_already_exists(self, file_paths=[]):
        """
        Validate that there are no duplicate display names in the repo
        """
        is_valid = True
        pack_names = []
        if file_paths:
            pack_names = get_pack_display_name_from_file_in_pack(file_paths)
        query_results = self.graph.get_duplicate_pack_display_name(pack_names)

        if query_results:
            for query_result in query_results:
                content_id = query_result[0]
                duplicate_names_id = query_result[1]
                error_message, error_code = Errors.duplicate_display_name(
                    content_id, duplicate_names_id
                )
                if self.handle_error(error_message, error_code, ""):
                    is_valid = False

        return is_valid

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator, error_codes
from demisto_sdk.commands.content_graph.interface.neo4j.neo4j_graph import \
    Neo4jContentGraphInterface as ContentGraphInterface


class GraphValidator(ContentGraphInterface, BaseValidator):
    """GraphValidator makes validations on the content graph.

    Attributes:
        _is_valid (bool): Whether the conf.json file current state is valid or not.
        conf_data (dict): The data from the conf.json file in our repo.
    """

    def __init__(self, specific_validations=None):
        BaseValidator.__init__(self, specific_validations=specific_validations)
        self.graph = ContentGraphInterface()

    def is_valid_graph(self) -> bool:
        return all(
            self.are_all_uses_relationships_paths_valid(),
        )

    @error_codes('GR100')
    def are_all_uses_relationships_paths_valid(self):
        """Validate that all USES relationship paths are valid, i.e.:
        1. Source's marketplaces field is a subset of the target's marketplaces field
        2. Source's fromvesion-toversion range intersects with target's fromvesion-toversion range.
        """
        paths_with_bad_marketplaces = self.graph.find_uses_paths_with_bad_marketplaces()
        paths_with_bad_versions = self.graph.find_uses_paths_with_bad_versions()

        # source_path, target_id, source_marketplaces, target_marketplaces, path_ids:
        for marketplaces_error_details in paths_with_bad_marketplaces:
            file_path = marketplaces_error_details['source_path']
            error_message, error_code = Errors.uses_with_bad_marketplaces(**marketplaces_error_details)
            if self.handle_error(error_message, error_code, file_path):
                return False

        # source_path, target_id, source_fromversion, source_toversion, target_fromversion, target_toversion, path_ids:
        for versions_error_details in paths_with_bad_versions:
            file_path = marketplaces_error_details['source_path']
            error_message, error_code = Errors.uses_with_bad_versions(**versions_error_details)
            if self.handle_error(error_message, error_code):
                return False

        return True

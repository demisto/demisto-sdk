from functools import cached_property
from pathlib import Path
from typing import List, Optional, Set

import pydantic

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import get_file, get_value
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.yaml_content_item import (
    YAMLContentItemParser,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StructureError,
)
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule import (
    StrictModelingRule,
)
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule_schema import (
    StrictModelingRuleSchema,
)


class ModelingRuleParser(YAMLContentItemParser, content_type=ContentType.MODELING_RULE):
    def __init__(
        self,
        path: Path,
        pack_marketplaces: List[MarketplaceVersions],
        pack_supported_modules: List[str],
        git_sha: Optional[str] = None,
    ) -> None:
        super().__init__(
            path, pack_marketplaces, pack_supported_modules, git_sha=git_sha
        )

    @cached_property
    def field_mapping(self):
        super().field_mapping.update(
            {"object_id": "id", "schema_key": "schema", "rules_key": "rules"}
        )
        return super().field_mapping

    @property
    def schema_key(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("schema_key", ""))

    @property
    def rules_key(self) -> Optional[str]:
        return get_value(self.yml_data, self.field_mapping.get("rules_key", ""))

    @property
    def supported_marketplaces(self) -> Set[MarketplaceVersions]:
        return {
            MarketplaceVersions.MarketplaceV2,
            MarketplaceVersions.PLATFORM,
        }

    @property
    def strict_object(self):
        raise NotImplementedError("This object has a different behavior")

    def validate_structure(self) -> List[StructureError]:
        """
        This method uses the parsed data and attempts to build a Pydantic (strict) object from it.
        Whenever the data and schema mismatch, we store the error using the 'structure_errors' attribute,
        which will be read during the ST110 validation run.
        In ModelingRule, we need to check two files: the schema json and the yml, so we override the
        method for combing all the pydantic errors from the both files.
        """
        directory_pydantic_error = []
        directory = self.path if self.path.is_dir() else self.path.parent
        for file in directory.iterdir():
            try:
                if file.suffix == ".yml":
                    StrictModelingRule.parse_obj(get_file(file))
                elif file.suffix == ".json":
                    StrictModelingRuleSchema.parse_obj(get_file(file))
            except pydantic.error_wrappers.ValidationError as e:
                directory_pydantic_error += [
                    StructureError(path=file, **error) for error in e.errors()
                ]
        return directory_pydantic_error

from typing import List

import pydantic

from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.parsers.modeling_rule import ModelingRuleParser
from demisto_sdk.commands.content_graph.strict_objects.asset_modeling_rule import (
    StrictAssetsModelingRule,
)
from demisto_sdk.commands.content_graph.strict_objects.asset_modeling_rule_schema import (
    StrictAssetsModelingRuleSchema,
)
from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    StructureError,
)


class AssetsModelingRuleParser(
    ModelingRuleParser, content_type=ContentType.ASSETS_MODELING_RULE
):
    @property
    def description(self) -> str:
        return "Collect assets and vulnerabilities"

    @property
    def strict_object(self):
        raise NotImplementedError("This object has a different behavior")

    def validate_structure(self) -> List[StructureError]:
        """
        This method uses the parsed data and attempts to build a Pydantic (strict) object from it.
        Whenever the data and schema mismatch, we store the error using the 'structure_errors' attribute,
        which will be read during the ST110 validation run.
        In AssetModelingRule, we need to check two files: the schema json and the yml, so we override the
        method for combing all the pydantic errors from the both files.
        """
        directory_pydantic_error = []
        directory = self.path if self.path.is_dir() else self.path.parent
        for file in directory.iterdir():
            try:
                if file.suffix == ".yml":
                    StrictAssetsModelingRule.parse_obj(get_file(file))
                elif file.suffix == ".json":
                    StrictAssetsModelingRuleSchema.parse_obj(get_file(file))
            except pydantic.error_wrappers.ValidationError as e:
                directory_pydantic_error += [
                    StructureError(path=file, **error) for error in e.errors()
                ]
        return directory_pydantic_error

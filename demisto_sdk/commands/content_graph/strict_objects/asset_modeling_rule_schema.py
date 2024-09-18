from demisto_sdk.commands.content_graph.strict_objects.common import create_model
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule_schema import (
    StrictModelingRuleSchema,
)

"""
The `AssetsModelingRule` and `ModelingRule` objects use the same schema, use use separate classes to make future diversions easier.
"""

StrictAssetsModelingRuleSchema = create_model(
    model_name="StrictAssetsModelingRule",
    base_models=(StrictModelingRuleSchema,),
)

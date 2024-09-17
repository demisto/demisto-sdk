from demisto_sdk.commands.content_graph.strict_objects.common import create_model
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule_schema import (
    StrictModelingRuleSchema,
)

# This model/class represents the StrictAssetsModelingRuleSchema.
# The AssetsModelingRuleSchema and ModelingRuleSchema objects have the same schema,
# but they are separate for future changes.


StrictAssetsModelingRuleSchema = create_model(
    model_name="StrictAssetsModelingRule",
    base_models=(StrictModelingRuleSchema,),
)

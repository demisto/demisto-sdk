from demisto_sdk.commands.content_graph.strict_objects.common import create_model
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule import (
    StrictModelingRule,
)

# This model/class represents the StrictAssetsModelingRule.
# The AssetsModelingRule and ModelingRule objects have the same schema, but they are separate for future changes.


StrictAssetsModelingRule = create_model(
    model_name="StrictAssetsModelingRule",
    base_models=(StrictModelingRule,),
)

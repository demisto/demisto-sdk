from demisto_sdk.commands.content_graph.strict_objects.common import create_model
from demisto_sdk.commands.content_graph.strict_objects.modeling_rule import (
    StrictModelingRule,
)

"""
The `AssetsModelingRule` and `ModelingRule` objects use the same schema, use use separate classes to make future diversions easier.
"""


StrictAssetsModelingRule = create_model(
    model_name="StrictAssetsModelingRule",
    base_models=(StrictModelingRule,),
)

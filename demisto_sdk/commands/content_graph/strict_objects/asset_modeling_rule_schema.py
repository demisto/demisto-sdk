from demisto_sdk.commands.content_graph.strict_objects.modeling_rule_schema import (
    StrictModelingRuleSchema,
)


class StrictAssetsModelingRuleSchema(StrictModelingRuleSchema):
    """
    The `AssetsModelingRule` and `ModelingRule` objects use the same schema, use use separate classes to make future diversions easier.
    """

    pass

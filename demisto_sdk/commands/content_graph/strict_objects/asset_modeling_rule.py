from demisto_sdk.commands.content_graph.strict_objects.modeling_rule import (
    StrictModelingRule,
)


class StrictAssetsModelingRule(StrictModelingRule):  # type: ignore[misc, valid-type]
    """
    The `AssetsModelingRule` and `ModelingRule` objects use the same schema, use separate classes to make
    future diversions easier.
    """

    pass

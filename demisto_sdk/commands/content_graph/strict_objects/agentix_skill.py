from typing import Optional

from pydantic import Extra

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)


class StrictAgentixSkill(AgentixBase):
    """Strict-validation model for an ``AgentixSkill`` content item.

    Inherits the ``AgentixBase`` schema (which requires ``commonfields`` with
    ``id`` and ``version``, plus the common fields ``name``, ``description``,
    ``tags``, ``category``, ``disabled``, ``internal``, ``fromversion``,
    ``toversion``, ``marketplaces``, ``supportedModules``,
    ``supportedFeatures``). Adds the skill-specific ``content`` field.
    """

    class Config:
        """
        Unknown top-level fields are ignored (not forbidden), so a skill carrying
        a field not yet defined in this schema does not fail ST110.
        """

        extra = Extra.ignore

    content: Optional[str] = None

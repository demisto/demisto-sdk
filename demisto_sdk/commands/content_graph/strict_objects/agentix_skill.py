from typing import Optional

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)


class StrictAgentixSkill(AgentixBase):
    """Strict-validation model for an ``AgentixSkill`` content item.

    Inherits the ``AgentixBase`` schema (which requires ``commonfields`` with
    ``id`` and ``version``, plus the common fields ``name``, ``description``,
    ``tags``, ``category``, ``disabled``, ``internal``, ``fromversion``,
    ``toversion``, ``marketplaces``, ``supportedModules``). Adds the
    skill-specific ``display`` and ``content`` fields.
    """

    display: Optional[str] = None
    content: Optional[str] = None

from pydantic import Field

from demisto_sdk.commands.content_graph.strict_objects.base_strict_model import (
    AgentixBase,
)


class AgentixAgent(AgentixBase):
    color: str = Field(
        ...,
        description="Display color of the agent in the UI (hex color code, e.g. '#FF5733'). Used to visually distinguish agents.",
    )
    visibility: str = Field(
        ...,
        description="Visibility scope of the agent. Controls who can see and use this agent (e.g. 'public', 'private').",
    )
    actionids: list[str] = Field(
        [],
        description="List of action IDs (AgentixAction names) that this agent is allowed to invoke. Empty list means no actions are assigned.",
    )
    systeminstructions: str = Field(
        "",
        description="System-level instructions provided to the AI model that define the agent's persona, behavior, and constraints. Supports markdown.",
    )
    conversationstarters: list[str] = Field(
        [],
        description="List of suggested conversation starter prompts shown to users when they first interact with this agent.",
    )
    builtinactions: list[str] = Field(
        [],
        description="List of built-in platform action IDs that this agent can use in addition to its assigned actions.",
    )
    autoenablenewactions: bool = Field(
        False,
        description="When True, newly created actions are automatically enabled for this agent. Defaults to False.",
    )
    roles: list[str] = Field(
        [],
        description="List of XSOAR roles that are allowed to interact with this agent. Empty list means all roles can access it.",
    )
    sharedwithroles: list[str] = Field(
        [],
        description="List of XSOAR roles this agent is shared with. Controls visibility and access in multi-tenant environments.",
    )

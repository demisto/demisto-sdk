from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, validator

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class ActionDetail(BaseStrictModel):
    """An action invocation within a test outcome."""

    action_name: str
    arguments: Optional[Dict[str, Any]] = None


class EvaluationOutcome(BaseStrictModel):
    """A single expected outcome block."""

    evaluation_mode: Optional[Literal["any_of", "sequence"]] = None
    actions: Optional[List[ActionDetail]] = None
    expected_error: Optional[str] = None
    expected_output: Optional[str] = None


class AgentixActionTestCase(BaseStrictModel):
    """A single test case."""

    name: Optional[str] = None
    agent_id: str = Field("", alias="agent_id")
    expected_outcomes: Optional[List[EvaluationOutcome]] = None


class StrictAgentixActionTest(BaseStrictModel):
    """Top-level agentix action test file model."""

    tests: List[AgentixActionTestCase] = Field(default_factory=list)
    fixtures: Optional[List[str]] = None

from typing import Any, Dict, List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from demisto_sdk.commands.content_graph.strict_objects.common import (
    BaseStrictModel,
)


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

    @model_validator(mode="before")
    @classmethod
    def validate_action_logic(cls, data):
        actions = data.get("actions")
        # Handle both 'action' and 'actions' as seen in AG109
        action = data.get("action")
        expected_error = data.get("expected_error")
        evaluation_mode = data.get("evaluation_mode")

        # Error Handling rule: If expected_error is present, actions should be empty
        # unless in sequence mode for recovery.
        if expected_error and (actions or action) and evaluation_mode != "sequence":
            raise ValueError(
                "expected_error requires no actions unless using 'sequence' mode for recovery."
            )

        if not expected_error and actions is None and not action:
            raise ValueError("Either 'expected_error' or 'actions' must be provided.")

        return data


class AgentixActionTestCase(BaseStrictModel):
    """A single test case."""

    name: Optional[str] = None
    prompt: Optional[str] = None
    agent_id: str = Field("", alias="agent_id")
    expected_outcomes: Optional[List[EvaluationOutcome]] = None
    any_of: Optional[List[EvaluationOutcome]] = None
    sequence: Optional[List[EvaluationOutcome]] = None

    @model_validator(mode="before")
    @classmethod
    def validate_modes(cls, data):
        modes = {"any_of", "sequence", "expected_outcomes"}
        present_modes = modes.intersection(data.keys())
        if len(present_modes) > 1:
            raise ValueError(
                f"Multiple evaluation modes present: {', '.join(present_modes)}. Only one is allowed."
            )
        return data

    @field_validator("prompt")
    @classmethod
    def prompt_must_end_with_period(cls, v):
        if v and not v.strip().endswith("."):
            raise ValueError("Prompt must end with a period (.).")
        return v


class StrictAgentixActionTest(BaseStrictModel):
    """Top-level agentix action test file model."""

    tests: List[AgentixActionTestCase] = Field(default_factory=list)
    fixtures: Optional[List[str]] = None

from typing import Any, Dict, List, Optional

from pydantic import Field, root_validator, validator

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class ActionDetail(BaseStrictModel):
    action_id: str
    arguments: Optional[Dict[str, Any]] = None


class EvaluationOutcome(BaseStrictModel):
    evaluation_mode: Optional[str] = Field(
        None, description="e.g., 'any_of' or 'sequence'"
    )
    actions: List[ActionDetail] = []
    expected_error: Optional[str] = None

    @root_validator(pre=True)
    def validate_action_logic(cls, values):
        actions = values.get("actions")
        # Handle both 'action' and 'actions' as seen in AG109
        action = values.get("action")
        expected_error = values.get("expected_error")
        evaluation_mode = values.get("evaluation_mode")

        # Error Handling rule: If expected_error is present, actions should be empty
        # unless in sequence mode for recovery.
        if expected_error and (actions or action) and evaluation_mode != "sequence":
            raise ValueError(
                "expected_error requires no actions unless using 'sequence' mode for recovery."
            )

        if not expected_error and actions is None and not action:
            raise ValueError("Either 'expected_error' or 'actions' must be provided.")

        return values


class AgentixActionTestCase(BaseStrictModel):
    name: str = "Unnamed Test"
    prompt: str = ""
    agent_id: str = Field("", alias="agent_id")
    expected_outcomes: Optional[List[EvaluationOutcome]] = None
    any_of: Optional[List[EvaluationOutcome]] = None
    sequence: Optional[List[EvaluationOutcome]] = None

    @root_validator(pre=True)
    def validate_modes(cls, values):
        modes = {"any_of", "sequence", "expected_outcomes"}
        present_modes = modes.intersection(values.keys())
        if len(present_modes) > 1:
            raise ValueError(
                f"Multiple evaluation modes present: {', '.join(present_modes)}. Only one is allowed."
            )
        return values

    @validator("prompt")
    def prompt_must_end_with_period(cls, v):
        if v and not v.strip().endswith("."):
            raise ValueError("Prompt must end with a period (.).")
        return v


class AgentixActionTestFile(BaseStrictModel):
    tests: List[AgentixActionTestCase]

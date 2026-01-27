from typing import List, Optional, Union, Dict, Any
from pydantic import Field, validator, root_validator

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class ActionDetail(BaseStrictModel):
    action_id: str
    arguments: Optional[Dict[str, Any]] = None


class EvaluationOutcome(BaseStrictModel):
    evaluation_mode: Optional[str] = Field(None, description="e.g., 'any_of' or 'sequence'")
    actions: List[ActionDetail] = []
    expected_error: Optional[str] = None

    @root_validator(pre=True)
    def validate_action_logic(cls, values):
        actions = values.get("actions", [])
        expected_error = values.get("expected_error")

        # Error Handling rule: If expected_error is present, actions should be empty
        # unless in sequence mode for recovery.
        if expected_error and actions and values.get("evaluation_mode") != "sequence":
            raise ValueError("expected_error requires no actions unless using 'sequence' mode for recovery.")

        return values


class AgentixTestCase(BaseStrictModel):
    name: str = "Unnamed Test"
    prompt: str = ""
    agent_id: str = Field("", alias="agent_id")
    expected_outcomes: Optional[List[EvaluationOutcome]] = None

    @validator("prompt")
    def prompt_must_end_with_period(cls, v):
        if v and not v.strip().endswith("."):
            raise ValueError("Prompt must end with a period (.).")
        return v


class AgentixTestFile(BaseStrictModel):
    tests: List[AgentixTestCase]
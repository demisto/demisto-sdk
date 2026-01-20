from typing import List, Optional

from pydantic import Field, validator

from demisto_sdk.commands.content_graph.strict_objects.common import BaseStrictModel


class ExpectedOutcome(BaseStrictModel):
    action: Optional[str] = None
    actions: Optional[List[str]] = None
    arguments: Optional[dict] = None
    expected_error: Optional[str] = Field(None, alias="expected_error")


class AgentixTestCase(BaseStrictModel):
    name: str = "Unnamed Test"
    prompt: str = ""
    agent_id: str = Field("", alias="agent_id")
    expected_outcomes: Optional[List[ExpectedOutcome]] = None
    any_of: Optional[List[ExpectedOutcome]] = None
    sequence: Optional[List[ExpectedOutcome]] = None

    @validator("prompt")
    def prompt_must_end_with_period(cls, v):
        if v and not v.strip().endswith("."):
            raise ValueError("Prompt must end with a period (.).")
        return v


class AgentixTestFile(BaseStrictModel):
    tests: List[AgentixTestCase]

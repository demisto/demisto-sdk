from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated


class EventLog(BaseModel):
    test_data_event_id: UUID = Field(default_factory=uuid4)
    vendor: Optional[str] = None
    product: Optional[str] = None
    dataset: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = {}
    expected_values: Optional[Dict[str, Any]] = {}


def event_log_validator(v: EventLog):
    if not v.expected_values:
        err = "The expected values mapping is required for each test data event"
        raise ValidationError(err)
    for k in v.expected_values.keys():
        if k == "_time":
            continue
        if not k.casefold().startswith("xdm."):
            err = "The expected values mapping keys are expected to start with 'xdm.' (case insensitive)"
            raise ValidationError(err)
    return v


EventLogType = Annotated[EventLog, AfterValidator(event_log_validator)]


class TestData(BaseModel):
    data: List[EventLogType] = Field(default_factory=lambda: [EventLog()])


class CompletedTestData(TestData):
    @field_validator("data")
    @classmethod
    def validate_expected_values(cls, v):
        for test_data_event in v:
            if not test_data_event.expected_values or not any(
                test_data_event.expected_values.values()
            ):
                err = "The expected values mapping is required for each test data event"
                if not any(test_data_event.expected_values.values()):
                    err = (
                        "No values were provided in expected values mapping - all were null"
                        " - you must provide at least one"
                    )
                raise ValueError(err)
        return v

    @field_validator("data")
    @classmethod
    def validate_event_data(cls, v):
        for test_data_event in v:
            if not test_data_event.event_data:
                err = "The event data is required for each test data event"
                raise ValueError(err)
        return v

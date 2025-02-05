from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated


class Validations(str, Enum):
    SCHEMA_TYPES_ALIGNED_WITH_TEST_DATA = "schema_test_data_types"
    TEST_DATA_CONFIG_IGNORE = "test_data_config_ignore"

    @classmethod
    def as_set(cls):
        return set(map(lambda attr: attr.value, cls))  # type: ignore[misc, attr-defined]


class EventLog(BaseModel):
    test_data_event_id: UUID = Field(default_factory=uuid4)
    vendor: Optional[str] = None
    product: Optional[str] = None
    dataset: Optional[str] = None
    tenant_timezone: Optional[str] = "UTC"
    event_data: Optional[Dict[str, Any]] = {}
    expected_values: Optional[Dict[str, Any]] = {}

    @field_validator("test_data_event_id")
    @classmethod
    def validate_test_data(cls, v):
        v = uuid4()
        return v


def validate_expected_values(v: EventLog) -> EventLog:
    """A validator for a single EventLog item in TestData.data"""
    if v.expected_values:
        for k in v.expected_values.keys():
            if k == "_time":  # '_time' is a special field without the 'xdm.' prefix.
                continue
            if not k.casefold().startswith("xdm."):
                err = "The expected values mapping keys are expected to start with 'xdm.' (case insensitive)"
                raise ValueError(err)
    return v


class TestData(BaseModel):
    data: List[
        Annotated[EventLog, field_validator(validate_expected_values, mode="after")]
    ] = Field(
        default_factory=lambda: [EventLog(expected_values={"xdm.example": "value"})]
    )
    ignored_validations: List[str] = []

    @field_validator("ignored_validations")
    @classmethod
    def validate_ignored_validations(cls, v):
        provided_ignored_validations = set(v)
        valid_ignored_validations = Validations.as_set()
        if (
            invalid_validation_names := provided_ignored_validations
            - valid_ignored_validations
        ):
            raise ValueError(
                f"The following validation names {invalid_validation_names} are invalid, "
                f"please make sure validations are named one of {valid_ignored_validations}"
            )
        return v


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

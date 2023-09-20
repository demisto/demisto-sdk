from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


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

    @validator("test_data_event_id")
    def validate_test_data(cls, v):
        v = uuid4()
        return v


class TestData(BaseModel):
    data: List[EventLog] = Field(default_factory=lambda: [EventLog()])
    ignored_validations: List[str] = []

    @validator("data", each_item=True)
    def validate_expected_values(cls, v):
        for k in v.expected_values.keys():
            if k == "_time":  # '_time' is a special field without the 'xdm.' prefix.
                continue
            if not k.casefold().startswith("xdm."):
                err = "The expected values mapping keys are expected to start with 'xdm.' (case insensitive)"
                raise ValueError(err)
        return v

    @validator("ignored_validations")
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
    @validator("data")
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

    @validator("data")
    def validate_event_data(cls, v):
        for test_data_event in v:
            if not test_data_event.event_data:
                err = "The event data is required for each test data event"
                raise ValueError(err)
        return v

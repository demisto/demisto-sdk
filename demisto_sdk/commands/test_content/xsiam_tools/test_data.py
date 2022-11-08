from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, root_validator, validator


class EventLog(BaseModel):
    test_data_event_id: UUID = Field(default_factory=uuid4)
    event_data: Optional[Union[str, Dict[str, Any]]] = {}


class ExpectedOutputs(BaseModel):
    test_data_event_id: UUID = Field(default_factory=uuid4)
    mapping: Optional[Dict[str, Any]] = {}


class TestData(BaseModel):
    data: List[EventLog] = Field(default_factory=lambda: [EventLog()])
    expected_values: List[ExpectedOutputs] = Field(default_factory=lambda: [ExpectedOutputs()])

    @root_validator()
    def validate(cls, values):
        if len(values['data']) != len(values['expected_values']):
            raise ValueError("The number of data and expected values must match")
        elif any(
            [
                d.test_data_event_id != e.test_data_event_id for d, e in
                zip(values['data'], values['expected_values'])
            ]
        ):
            for d, e in zip(values['data'], values['expected_values']):
                e.test_data_event_id = d.test_data_event_id
        return values

    @validator('expected_values', each_item=True)
    def validate_expected_values(cls, v):
        for k in v.mapping.keys():
            if not k.casefold().startswith('xdm.'):
                err = "The expected values mapping keys are expected to start with 'xdm.' (case insensitive)"
                raise ValueError(err)
        return v

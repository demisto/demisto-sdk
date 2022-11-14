from uuid import UUID, uuid4
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


class EventLog(BaseModel):
    test_data_event_id: UUID = Field(default_factory=uuid4)
    vendor: Optional[str] = None
    product: Optional[str] = None
    dataset: Optional[str] = None
    event_data: Optional[Union[str, Dict[str, Any]]] = {}
    mapping: Optional[Dict[str, Any]] = {}


class TestData(BaseModel):
    data: List[EventLog] = Field(default_factory=lambda: [EventLog()])

    @validator('data', each_item=True)
    def validate_expected_values(cls, v):
        for k in v.mapping.keys():
            if not k.casefold().startswith('xdm.'):
                err = "The expected values mapping keys are expected to start with 'xdm.' (case insensitive)"
                raise ValueError(err)
        return v

from pydantic import BaseModel, Extra

class BaseStrictModel(BaseModel):
    class Config:
        extra = Extra.forbid
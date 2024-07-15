import pydantic
from pydantic import BaseModel

# TODO - documentation


def create_model(model_name: str, base_models: tuple, **kwargs) -> BaseModel:
    return pydantic.create_model(
        __model_name=model_name, __base__=base_models, **kwargs
    )  # type:ignore[call-overload]
